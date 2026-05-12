import json
import logging

import redis as redis_lib
from django.conf import settings

logger = logging.getLogger(__name__)

_redis_pool = None


def _get_redis_pool():
    """Return a shared Redis connection pool, created once per process."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis_lib.ConnectionPool.from_url(settings.CELERY_BROKER_URL)
    return _redis_pool


def get_redis_client():
    """Return a Redis client backed by the shared connection pool."""
    return redis_lib.Redis(connection_pool=_get_redis_pool())


def publish_progress(channel: str, data: dict):
    """Publish progress data to a Redis pub/sub channel.

    Channel naming: 'jobs.{job_id}' for job streams, 'notifications.{user_id}' for user alerts.

    Returns True on success, False on failure (logs the error).
    """
    client = get_redis_client()
    try:
        client.publish(channel, json.dumps(data))
        return True
    except redis_lib.ConnectionError:
        logger.warning("Failed to publish to channel %s: Redis unavailable", channel, exc_info=True)
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass
