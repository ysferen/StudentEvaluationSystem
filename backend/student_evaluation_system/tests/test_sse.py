import json
import itertools
import pytest
from unittest.mock import patch, MagicMock
from core.services.sse import publish_progress


class TestSsePublish:
    @patch("core.services.sse.redis_lib.Redis.from_url")
    def test_publish_progress_sends_json(self, mock_from_url):
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client

        publish_progress("jobs.42", {"type": "progress", "current": 3, "total": 10})

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args[0]
        assert call_args[0] == "jobs.42"
        parsed = json.loads(call_args[1])
        assert parsed["type"] == "progress"
        assert parsed["current"] == 3
        assert parsed["total"] == 10


@pytest.mark.django_db
class TestEventStreamView:
    def test_missing_channels_returns_400(self, authenticated_client):
        client, user = authenticated_client("sse_test1")
        response = client.get("/api/core/events/")
        assert response.status_code == 400
        assert "channels" in response.json()["error"]

    def test_unauthorized_notification_channel(self, authenticated_client, student_user_factory):
        """User cannot subscribe to another user's notification channel."""
        other_user = student_user_factory(username="sse_other")
        client, user = authenticated_client("sse_viewer")
        response = client.get(f"/api/core/events/?channels=notifications.{other_user.id}")
        assert response.status_code == 403

    @patch("core.views.sse.get_redis_client")
    def test_valid_channel_returns_sse_stream(self, mock_get_redis, authenticated_client):
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None  # No messages, just heartbeats
        mock_client = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_client

        client, user = authenticated_client("sse_stream_test")
        response = client.get("/api/core/events/?channels=jobs.1")

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache"

    @patch("core.views.sse.get_redis_client")
    def test_stream_receives_published_message(self, mock_get_redis, authenticated_client):
        mock_pubsub = MagicMock()

        # Return one message then None for subsequent calls (heartbeats)
        _call_count = [0]
        messages = [
            {"type": "message", "data": json.dumps({"type": "progress", "current": 1, "total": 5}).encode()},
        ]

        def get_message_side_effect(*args, **kwargs):
            idx = _call_count[0]
            _call_count[0] += 1
            if idx < len(messages):
                return messages[idx]
            return None

        mock_pubsub.get_message.side_effect = get_message_side_effect
        mock_client = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_client

        client, user = authenticated_client("sse_msg_test")
        response = client.get("/api/core/events/?channels=jobs.1")
        # Consume only a few chunks from the infinite stream
        chunks = list(itertools.islice(response.streaming_content, 5))
        content = b"".join(chunks)

        assert b"data:" in content
        assert b"progress" in content
