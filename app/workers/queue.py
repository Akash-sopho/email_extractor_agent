"""RQ queue setup placeholder (Task F)."""

import rq
from redis import Redis

from app.core.config import get_settings


def get_queue(name: str = "default") -> rq.Queue:
    settings = get_settings()
    conn = Redis.from_url(settings.REDIS_URL)
    return rq.Queue(name, connection=conn)

