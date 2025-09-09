from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import api_key_auth
from app.workers.queue import get_queue
from app.workers.jobs import extract_quotes_for_email

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.post("/email/{email_id}")
def reprocess_email(email_id: int) -> dict[str, Any]:
    """Enqueue extraction for a given email id and return job id."""
    q = get_queue("default")
    job = q.enqueue(extract_quotes_for_email, email_id)
    return {"status": "accepted", "job_id": job.get_id(), "email_id": email_id}
