from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import api_key_auth
from app.db.session import get_db
from app.gmail.client import GmailClient
from app.gmail.ingest import sync_threads
from app.local.ingest import ingest_eml_files

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


@router.post("/local")
def run_local_ingest_job(
    payload: dict | None = None, db=Depends(get_db)
) -> dict[str, Any]:
    """Ingest local .eml files from a directory (defaults to `sample/`).

    Body example:
      { "directory": "sample", "pattern": "*.eml", "enqueue": true }
    """
    params = payload or {}
    directory = params.get("directory", "sample")
    pattern = params.get("pattern", "*.eml")
    enqueue = bool(params.get("enqueue", True))
    result = ingest_eml_files(db, directory=directory, pattern=pattern, enqueue=enqueue)
    return {"status": "completed", **result}
