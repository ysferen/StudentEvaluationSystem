import json
import redis as redis_lib
from django.conf import settings


def get_redis_client():
    return redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)


def publish_progress(channel: str, data: dict):
    """Publish progress data to a Redis pub/sub channel.

    Channel naming: 'jobs.{job_id}' for job streams, 'notifications.{user_id}' for user alerts.
    """
    client = get_redis_client()
    client.publish(channel, json.dumps(data))
