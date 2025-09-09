"""Run an RQ worker (placeholder)."""

from rq import Connection, Worker

from app.core.config import get_settings
from app.workers.queue import get_queue


def main() -> None:
    settings = get_settings()
    queue = get_queue("default")
    with Connection(queue.connection):
        Worker([queue]).work()


if __name__ == "__main__":
    main()

