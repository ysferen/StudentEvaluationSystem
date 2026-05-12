import time
from collections.abc import Generator
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from core.services.sse import get_redis_client


def _validate_channels(request: Request) -> list[str] | Response:
    """Validate and return channel list, or an error Response."""
    channels = request.GET.get("channels", "")
    if not channels:
        return Response({"error": "channels query parameter required"}, status=400)

    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    return channel_list


def _check_notification_permissions(request: Request, channel_list: list[str]) -> Response | None:
    """Ensure users can only subscribe to their own notification channel."""
    for ch in channel_list:
        if ch.startswith("notifications."):
            user_id = ch.split(".", 1)[1]
            if str(user_id) != str(request.user.id):
                return Response(
                    {"error": "Cannot subscribe to another user's notification channel"},
                    status=403,
                )
    return None


def _event_generator(channel_list: list[str]) -> Generator[bytes, None, None]:
    """Yield SSE-formatted events from Redis pub/sub channels."""
    client = get_redis_client()
    pubsub = client.pubsub()
    try:
        pubsub.subscribe(*channel_list)
    except Exception:
        return

    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
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
        try:
            pubsub.unsubscribe(*channel_list)
        except Exception:
            pass


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_stream(request):
    """SSE endpoint. Subscribe via ?channels=jobs.42,notifications.5"""
    channels_or_error = _validate_channels(request)
    if isinstance(channels_or_error, Response):
        return channels_or_error

    permission_error = _check_notification_permissions(request, channels_or_error)
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
