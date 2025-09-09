from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import api_key_auth
from app.db.session import get_db
from app.gmail.client import GmailClient
from app.gmail.ingest import sync_threads

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.post("/run")
def run_ingest_job(
    payload: dict | None = None, db=Depends(get_db)
) -> dict[str, Any]:
    # Synchronous ingest (basic) — Task F will enqueue as a background job.
    params = payload or {}
    client = GmailClient()
    service = client.get_service()
    result = sync_threads(
        service,
        db,
        label=params.get("label"),
        query=params.get("query"),
        after=params.get("after"),
        before=params.get("before"),
        max_results=int(params.get("max_results", 100)),
    )
    return {"status": "completed", **result}


# Reprocess endpoint belongs to /reprocess; implemented in app/api/reprocess.py
