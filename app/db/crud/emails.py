"""Email access helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.db.models import Email


def get_email_with_parts(db: Session, email_id: int) -> Email | None:
    return (
        db.query(Email)
        .options(joinedload(Email.bodies), joinedload(Email.attachments), joinedload(Email.thread))
        .filter(Email.id == email_id)
        .one_or_none()
    )

