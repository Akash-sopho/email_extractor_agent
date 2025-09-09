from fastapi import FastAPI

from app.api import health, ingest, quotes, vendors, threads, reprocess
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Email Elchemy", version="0.1.0")

    # Routers
    app.include_router(health.router, tags=["health"])
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
    app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
    app.include_router(threads.router, prefix="/threads", tags=["threads"])
    app.include_router(reprocess.router, prefix="/reprocess", tags=["reprocess"])

    return app


app = create_app()
