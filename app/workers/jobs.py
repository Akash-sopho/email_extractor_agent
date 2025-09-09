"""RQ job definitions for background processing (Task F)."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.extract.pipeline import process_email


def extract_quotes_for_email(email_id: int) -> dict:
    """Background job: run extraction pipeline for one email."""
    db = SessionLocal()
    try:
        result = process_email(db, email_id)
        return result
    finally:
        db.close()

