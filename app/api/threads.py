from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import api_key_auth
from app.db.models import Thread
from app.db.session import get_db
from app.schemas.dto import ThreadResponse

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.get("", response_model=list[ThreadResponse])
def list_threads(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ThreadResponse]:
    q = db.query(Thread).order_by(Thread.first_seen_at.desc()).limit(limit).offset(offset)
    threads = q.all()
    return [
        ThreadResponse(
            id=int(t.id),
            gmail_thread_id=t.gmail_thread_id,
            first_seen_at=t.first_seen_at.isoformat() if t.first_seen_at else None,
            last_synced_at=t.last_synced_at.isoformat() if t.last_synced_at else None,
        )
        for t in threads
    ]

