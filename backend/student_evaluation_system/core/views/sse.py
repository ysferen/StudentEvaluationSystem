import json
import re
import time
from collections.abc import Generator

import redis as redis_lib
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from core.serializers import JobProgressEventSerializer
from core.services.sse import get_redis_client


class SSERenderer(BaseRenderer):
    """Minimal renderer that accepts text/event-stream so DRF content negotiation
    does not reject EventSource requests before the view runs."""

    media_type = "text/event-stream"
    format = "sse"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # The view returns StreamingHttpResponse directly, so this is never called.
        return data


# Channel names must match: {prefix}.{identifier}
# Prefix: letters only (e.g. 'jobs', 'notifications')
# Identifier: alphanumeric with hyphens/underscores
_CHANNEL_RE = re.compile(r"^[a-z]+\.[a-zA-Z0-9_-]+$")
_MAX_CHANNEL_LENGTH = 128


def _validate_channels(request: Request) -> list[str] | Response:
    """Validate and return channel list, or an error Response."""
    channels = request.GET.get("channels", "")
    if not channels:
        return Response({"error": "channels query parameter required"}, status=400)

    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    for ch in channel_list:
        if len(ch) > _MAX_CHANNEL_LENGTH or not _CHANNEL_RE.match(ch):
            return Response(
                {"error": f"Invalid channel name: {ch}"},
                status=400,
            )
    return channel_list


def _check_permissions(request: Request, channel_list: list[str]) -> Response | None:
    """Ensure users can only subscribe to channels they own."""
    for ch in channel_list:
        if ch.startswith("notifications."):
            user_id = ch.split(".", 1)[1]
            if str(user_id) != str(request.user.id):
                return Response(
                    {"error": "Cannot subscribe to another user's notification channel"},
                    status=403,
                )
        elif ch.startswith("jobs."):
            if getattr(request.user, "is_admin_user", False):
                continue

            try:
                job_id = int(ch.split(".", 1)[1])
            except ValueError:
                return Response(
                    {"error": f"Invalid job channel: {ch}"},
                    status=400,
                )

            if not _job_owned_by_user(job_id, request.user):
                return Response(
                    {"error": "Cannot subscribe to another user's job channel"},
                    status=403,
                )

    return None


def _job_owned_by_user(job_id: int, user) -> bool:
    """Check whether the given job ID belongs to any known job model owned by the user."""
    from core.models import TermTransitionJob, WeightSuggestionJob
    from evaluation.models import ScoreRecomputeJob

    for model in (TermTransitionJob, ScoreRecomputeJob, WeightSuggestionJob):
        if model.objects.filter(id=job_id, triggered_by=user).exists():
            return True
    return False


def _subscribe(client, pubsub, channel_list: list[str]):
    """Subscribe to channels. Yields error event on failure. Returns True on success."""
    try:
        pubsub.subscribe(*channel_list)
    except redis_lib.ConnectionError:
        yield b'event: error\ndata: {"error": "Redis unavailable"}\n\n'
        yield False
        return
    except Exception:
        yield False
        return
    yield True


def _cleanup_pubsub(pubsub, client, channel_list):
    """Safely unsubscribe and close pubsub/client connections."""
    for cleanup in (
        lambda: pubsub.unsubscribe(*channel_list),
        lambda: pubsub.close(),
        lambda: client.close(),
    ):
        try:
            cleanup()
        except Exception:
            pass


def _get_job_for_channel(job_id: int) -> object | None:
    """Fetch any known job model instance by ID. Returns None if not found."""
    from core.models import TermTransitionJob, WeightSuggestionJob
    from evaluation.models import ScoreRecomputeJob

    for model in (TermTransitionJob, ScoreRecomputeJob, WeightSuggestionJob):
        try:
            return model.objects.get(id=job_id)
        except model.DoesNotExist:
            continue
    return None


def _build_initial_event(job) -> dict | None:
    """Build an SSE event payload representing the current state of a job."""
    from core.models import TermTransitionJob, WeightSuggestionJob
    from evaluation.models import ScoreRecomputeJob

    is_terminal = job.status in ("success", "failed")

    if isinstance(job, TermTransitionJob):
        total = len(job.template_ids) if job.template_ids else 0
        if is_terminal:
            event = {
                "type": "complete",
                "job_id": job.id,
                "status": job.status,
                "courses_created": job.courses_created,
                "total_templates": total,
            }
        else:
            event = {
                "type": "progress",
                "job_id": job.id,
                "status": job.status,
                "current": job.courses_created if job.status == "running" else 0,
                "total": total,
                "created": job.courses_created,
            }
    elif isinstance(job, ScoreRecomputeJob):
        event = {
            "type": "complete" if is_terminal else "progress",
            "job_id": job.id,
            "status": job.status,
            "task_type": job.task_type,
        }
    elif isinstance(job, WeightSuggestionJob):
        event = {
            "type": "complete" if is_terminal else "progress",
            "job_id": job.id,
            "status": job.status,
        }
        if job.result is not None:
            event["result"] = job.result
    else:
        return None

    if job.error:
        event["error"] = job.error
    return event


def _emit_initial_state(channel_list: list[str], request: Request) -> Generator[bytes, None, None]:
    """Emit the current DB state for each jobs.* channel so the client always
    receives the latest status, even if Redis pub/sub messages were lost."""
    for ch in channel_list:
        if not ch.startswith("jobs."):
            continue
        try:
            job_id = int(ch.split(".", 1)[1])
        except ValueError:
            continue

        job = _get_job_for_channel(job_id)
        if job is None:
            continue

        if not getattr(request.user, "is_admin_user", False) and job.triggered_by_id != request.user.id:
            continue

        event = _build_initial_event(job)
        if event is None:
            continue

        yield f"data: {json.dumps(event)}\n\n".encode()


def _event_generator(channel_list: list[str], request: Request) -> Generator[bytes, None, None]:
    """Yield SSE-formatted events from Redis pub/sub channels."""
    yield from _emit_initial_state(channel_list, request)

    client = get_redis_client()
    pubsub = client.pubsub()
    sub_gen = _subscribe(client, pubsub, channel_list)

    if next(sub_gen) is False:
        return

    try:
        while True:
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            except redis_lib.ConnectionError:
                yield b'event: error\ndata: {"error": "Redis connection lost"}\n\n'
                break

            if message and message.get("type") == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n".encode()
            else:
                yield b": heartbeat\n\n"
            time.sleep(0.1)
    except GeneratorExit:
        pass
    finally:
        _cleanup_pubsub(pubsub, client, channel_list)


@extend_schema(
    summary="Stream job progress via SSE",
    description="Subscribe to Redis pub/sub channels for real-time job progress updates. "
    "Pass comma-separated channel names via the `channels` query parameter "
    "(e.g. `?channels=jobs.42,notifications.5`).",
    responses={
        (200, "text/event-stream"): JobProgressEventSerializer,
    },
)
@api_view(["GET"])
@renderer_classes([JSONRenderer, SSERenderer])
@permission_classes([IsAuthenticated])
def event_stream(request):
    """SSE endpoint. Subscribe via ?channels=jobs.42,notifications.5"""
    channels_or_error = _validate_channels(request)
    if isinstance(channels_or_error, Response):
        return channels_or_error

    permission_error = _check_permissions(request, channels_or_error)
    if permission_error is not None:
        return permission_error

    response = StreamingHttpResponse(
        _event_generator(channels_or_error, request),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    # NOTE: Do NOT set Connection: keep-alive — wsgiref (Django dev server)
    # prohibits hop-by-hop headers. SSE connections are persistent by default.
    return response
