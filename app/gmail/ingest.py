"""Gmail ingestion: list threads, fetch messages, parse bodies, save attachments.

Public entrypoints:
- list_threads(...)
- sync_threads(...)
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Attachment, Email, EmailBody, Thread
from app.workers.queue import get_queue
from app.workers.jobs import extract_quotes_for_email
from app.gmail.parsers import extract_bodies_from_mime


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str | None) -> str:
    if not name:
        return "attachment"
    keep = "-_.() "
    sanitized = "".join(c for c in name if c.isalnum() or c in keep)
    return sanitized or "attachment"


def _parse_header(headers: list[dict[str, str]], name: str) -> str | None:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _b64url_decode(data: str) -> bytes:
    # Gmail uses URL-safe base64 without padding
    padding = 4 - (len(data) % 4)
    if padding and padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def list_threads(service: Any, *, label: str | None = None, query: str | None = None,
                 after: str | None = None, before: str | None = None, max_results: int = 100) -> list[dict[str, Any]]:
    q: list[str] = []
    if query:
        q.append(query)
    if label:
        q.append(f"label:{label}")
    if after:
        q.append(f"after:{after}")
    if before:
        q.append(f"before:{before}")
    qstr = " ".join(q) if q else None

    resp = service.users().threads().list(userId="me", q=qstr, maxResults=max_results).execute()
    return resp.get("threads", [])


def _get_or_create_thread(db: Session, gmail_thread_id: str, last_history_id: str | None) -> Thread:
    thread = db.query(Thread).filter_by(gmail_thread_id=gmail_thread_id).one_or_none()
    if thread is None:
        thread = Thread(gmail_thread_id=gmail_thread_id, last_history_id=last_history_id)
        db.add(thread)
        db.flush()
    else:
        if last_history_id:
            thread.last_history_id = last_history_id
    return thread


def _parse_address_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [v.strip() for v in value.split(",") if v.strip()]
    return parts or None


def _persist_email_and_parts(
    db: Session,
    thread: Thread,
    message_full: dict[str, Any],
    raw_bytes: bytes | None,
) -> Email:
    msg_id = message_full["id"]
    headers: list[dict[str, str]] = message_full.get("payload", {}).get("headers", [])
    from_addr = _parse_header(headers, "From")
    to_addrs = _parse_address_list(_parse_header(headers, "To"))
    cc_addrs = _parse_address_list(_parse_header(headers, "Cc"))
    subject = _parse_header(headers, "Subject")

    date_hdr = _parse_header(headers, "Date")
    sent_at: datetime | None = None
    if date_hdr:
        try:
            sent_at = parsedate_to_datetime(date_hdr)
        except Exception:
            sent_at = None

    snippet = message_full.get("snippet")
    raw_hash = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None

    email = db.query(Email).filter_by(gmail_message_id=msg_id).one_or_none()
    if email is None:
        email = Email(
            thread_id=thread.id,
            gmail_message_id=msg_id,
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            subject=subject,
            sent_at=sent_at,
            snippet=snippet,
            raw_hash=raw_hash,
        )
        db.add(email)
        db.flush()
    else:
        email.thread_id = thread.id
        email.from_addr = from_addr
        email.to_addrs = to_addrs
        email.cc_addrs = cc_addrs
        email.subject = subject
        email.sent_at = sent_at
        email.snippet = snippet
        email.raw_hash = raw_hash

    # Bodies
    plain_text, html_text = (None, None)
    if raw_bytes:
        plain_text, html_text = extract_bodies_from_mime(raw_bytes)
    # Store bodies if present (one row per type)
    if plain_text is not None:
        db.add(
            EmailBody(
                email_id=email.id,
                mime_type="text/plain",
                charset="utf-8",
                body_text=plain_text,
                body_html=None,
                body_hash=None,
            )
        )
    if html_text is not None:
        db.add(
            EmailBody(
                email_id=email.id,
                mime_type="text/html",
                charset="utf-8",
                body_text=None,
                body_html=html_text,
                body_hash=None,
            )
        )

    return email


def _iter_parts(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    stack = [payload]
    while stack:
        part = stack.pop()
        yield part
        for child in part.get("parts", []) or []:
            stack.append(child)


def _download_attachments(
    service: Any, db: Session, email: Email, message_id: str, payload: dict[str, Any]
) -> None:
    settings = get_settings()
    base_dir = Path("data") / "attachments" / message_id
    _ensure_dir(base_dir)

    for part in _iter_parts(payload):
        filename = part.get("filename")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        if not attachment_id or not filename:
            continue
        try:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            data = att.get("data")
            if not data:
                continue
            content = _b64url_decode(data)
        except Exception:
            continue

        safe_name = _safe_filename(filename)
        local_path = base_dir / safe_name
        with open(local_path, "wb") as f:
            f.write(content)

        db.add(
            Attachment(
                email_id=email.id,
                filename=filename,
                mime_type=part.get("mimeType"),
                size_bytes=body.get("size"),
                local_path=str(local_path),
            )
        )


def fetch_and_persist_message(service: Any, db: Session, thread: Thread, message_id: str) -> Email:
    # full for headers/parts; raw for RFC822 parse + hash
    full = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    raw_resp = service.users().messages().get(userId="me", id=message_id, format="raw").execute()
    raw_data = raw_resp.get("raw")
    raw_bytes = _b64url_decode(raw_data) if raw_data else None

    email = _persist_email_and_parts(db, thread, full, raw_bytes)
    _download_attachments(service, db, email, message_id, full.get("payload", {}))
    # Enqueue extraction job for this email
    try:
        q = get_queue("default")
        q.enqueue(extract_quotes_for_email, int(email.id))
    except Exception:
        # If Redis is not available, skip silently; reprocess can be triggered later
        pass
    return email


def sync_threads(
    service: Any,
    db: Session,
    *,
    label: str | None = None,
    query: str | None = None,
    after: str | None = None,
    before: str | None = None,
    max_results: int = 100,
) -> dict[str, int]:
    """List threads, pull all messages, persist thread/email/bodies/attachments.

    Dates should be strings as accepted by Gmail search (e.g., YYYY/MM/DD).
    """
    threads = list_threads(
        service, label=label, query=query, after=after, before=before, max_results=max_results
    )
    saved_emails = 0
    for th in threads:
        thread_id = th["id"]
        thread_res = service.users().threads().get(userId="me", id=thread_id).execute()
        history_id = thread_res.get("historyId")
        thread_obj = _get_or_create_thread(db, thread_id, str(history_id) if history_id else None)
        db.flush()
        for msg in thread_res.get("messages", []) or []:
            fetch_and_persist_message(service, db, thread_obj, msg["id"])
            saved_emails += 1

    db.commit()
    return {"threads": len(threads), "emails": saved_emails}
