import re
import time
from collections.abc import Generator

import redis as redis_lib
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from core.services.sse import get_redis_client

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
            # For job channels, verify user is admin or job owner
            if getattr(request.user, "is_admin_user", False):
                continue
            from core.models import TermTransitionJob

            try:
                job_id = int(ch.split(".", 1)[1])
            except ValueError:
                return Response(
                    {"error": f"Invalid job channel: {ch}"},
                    status=400,
                )
            if not TermTransitionJob.objects.filter(id=job_id, triggered_by=request.user).exists():
                return Response(
                    {"error": "Cannot subscribe to another user's job channel"},
                    status=403,
                )

    return None


def _subscribe(client, pubsub, channel_list: list[str]) -> bool:
    """Subscribe to channels. Yields error event on failure. Returns True on success."""
    try:
        pubsub.subscribe(*channel_list)
    except redis_lib.ConnectionError:
        yield b'event: error\ndata: {"error": "Redis unavailable"}\n\n'
        yield False  # signal failure
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


def _event_generator(channel_list: list[str]) -> Generator[bytes, None, None]:
    """Yield SSE-formatted events from Redis pub/sub channels."""
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


@api_view(["GET"])
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
        _event_generator(channels_or_error),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
