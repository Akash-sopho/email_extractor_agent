"""Ingest local .eml files and persist to DB, enqueue extraction.

This complements Gmail ingestion by allowing local development/testing with
sample emails stored on disk.
"""

from __future__ import annotations

import base64
import hashlib
from email import message_from_bytes
from email.message import Message
from email.utils import parsedate_to_datetime, getaddresses
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Attachment, Email, EmailBody, Thread
from app.extract.prompts import STRICT_JSON_SCHEMA
from app.gmail.parsers import extract_bodies_from_mime
from app.workers.queue import get_queue
from app.workers.jobs import extract_quotes_for_email


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str | None) -> str:
    if not name:
        return "attachment"
    keep = "-_.() "
    sanitized = "".join(c for c in name if c.isalnum() or c in keep)
    return sanitized or "attachment"


def _parse_address_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    addrs = [addr for _, addr in getaddresses([value]) if addr]
    return addrs or None


def _get_or_create_thread(db: Session, thread_key: str) -> Thread:
    thread = db.query(Thread).filter_by(gmail_thread_id=thread_key).one_or_none()
    if thread is None:
        thread = Thread(gmail_thread_id=thread_key, last_history_id=None)
        db.add(thread)
        db.flush()
    return thread


def _walk_parts(msg: Message):
    for part in msg.walk():
        if part.is_multipart():
            continue
        yield part


def _persist_email_and_parts(
    db: Session,
    thread: Thread,
    msg: Message,
    raw_bytes: bytes,
    message_key: str,
) -> Email:
    headers = msg
    from_addr = headers.get("From")
    to_addrs = _parse_address_list(headers.get("To"))
    cc_addrs = _parse_address_list(headers.get("Cc"))
    subject = headers.get("Subject")

    date_hdr = headers.get("Date")
    sent_at = None
    if date_hdr:
        try:
            sent_at = parsedate_to_datetime(date_hdr)
        except Exception:
            sent_at = None

    # Prefer text/plain body; fallback to HTML
    plain_text, html_text = extract_bodies_from_mime(raw_bytes)
    body_for_snippet = (plain_text or html_text or "").strip()
    snippet = body_for_snippet[:200] if body_for_snippet else None

    raw_hash = hashlib.sha256(raw_bytes).hexdigest()

    email = db.query(Email).filter_by(gmail_message_id=message_key).one_or_none()
    if email is None:
        email = Email(
            thread_id=thread.id,
            gmail_message_id=message_key,
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

    # Attachments
    base_dir = Path("data") / "attachments_local" / message_key
    _ensure_dir(base_dir)
    for part in _walk_parts(msg):
        filename = part.get_filename()
        if not filename:
            continue
        try:
            payload = part.get_payload(decode=True)
            if not payload:
                continue
        except Exception:
            continue

        safe_name = _safe_filename(filename)
        local_path = base_dir / safe_name
        try:
            with open(local_path, "wb") as f:
                f.write(payload)
        except Exception:
            continue

        db.add(
            Attachment(
                email_id=email.id,
                filename=filename,
                mime_type=(part.get_content_type() or None),
                size_bytes=len(payload),
                local_path=str(local_path),
            )
        )

    return email


def ingest_eml_files(
    db: Session,
    *,
    directory: str = "sample",
    pattern: str = "*.eml",
    enqueue: bool = True,
) -> dict[str, int]:
    """Process .eml files from `directory` and enqueue extraction for each.

    Returns counts: {"threads": X, "emails": Y}
    """
    dir_path = Path(directory)
    files = sorted(dir_path.glob(pattern))
    created_threads = 0
    saved_emails = 0

    for f in files:
        try:
            raw = f.read_bytes()
        except Exception:
            continue

        try:
            msg = message_from_bytes(raw)
        except Exception:
            continue

        # Unique message key: prefer Message-ID, else sha256 prefix
        msg_id_hdr = msg.get("Message-ID") or msg.get("Message-Id")
        if msg_id_hdr:
            message_key = f"local:{msg_id_hdr.strip()}"
        else:
            message_key = f"local:sha256:{hashlib.sha256(raw).hexdigest()[:16]}"

        # One thread per file by default (keeps it simple and deterministic)
        thread_key = f"local-thread:{f.stem}"
        # Create/get thread
        thread = db.query(Thread).filter_by(gmail_thread_id=thread_key).one_or_none()
        if thread is None:
            thread = Thread(gmail_thread_id=thread_key, last_history_id=None)
            db.add(thread)
            db.flush()
            created_threads += 1

        # Persist email, bodies, attachments
        email = _persist_email_and_parts(db, thread, msg, raw, message_key)

        # Enqueue extraction job
        if enqueue:
            try:
                q = get_queue("default")
                q.enqueue(extract_quotes_for_email, int(email.id))
            except Exception:
                # Skip if Redis not available; caller can reprocess later
                pass

        saved_emails += 1

    db.commit()
    return {"threads": created_threads, "emails": saved_emails}

