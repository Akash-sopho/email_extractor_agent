"""Helpers to extract text/plain and text/html from raw RFC822 messages."""

from __future__ import annotations

from email import message_from_bytes
from email.message import Message
from typing import Tuple


def _walk_parts(msg: Message) -> tuple[str | None, str | None]:
    plain: str | None = None
    html: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = (part.get_content_type() or "").lower()
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            except Exception:
                continue

            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
    else:
        ctype = (msg.get_content_type() or "").lower()
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/plain":
                plain = text
            elif ctype == "text/html":
                html = text

    return plain, html


def extract_bodies_from_mime(raw_message: bytes) -> Tuple[str | None, str | None]:
    """Return (plain_text, html_text) from a raw RFC822 email bytes."""
    try:
        msg = message_from_bytes(raw_message)
    except Exception:
        return None, None
    return _walk_parts(msg)

