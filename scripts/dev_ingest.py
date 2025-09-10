"""Dev ingest script: seed a fake email and run the pipeline end-to-end
without Gmail/Redis. This helps validate DB models, pipeline wiring, and
normalization in a controlled way.

Usage:
  python scripts/dev_ingest.py

Requirements:
  - DB schema applied (alembic upgrade head)
  - DATABASE_URL configured (e.g., via .env)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.db.session import SessionLocal
from app.db.models import Thread, Email, EmailBody
from app.extract import llm as llm_module
from app.extract.pipeline import process_email


BODY_TEXT = """
Hello,

Please find our quote below.

Items:
- Widget A x2 @ 100.00
- Widget B x1 @ 250.00

Subtotal: 450.00
Tax: 45.00
Shipping: 10.00
Total: 505.00

Valid till: 2030-01-31

Thanks,
ACME Sales
""".strip()


def seed_email(db) -> int:
    thread = Thread(gmail_thread_id="dev-thread-1")
    db.add(thread)
    db.flush()

    email = Email(
        thread_id=thread.id,
        gmail_message_id="dev-msg-1",
        from_addr="sales@acme.com",
        to_addrs=["you@example.com"],
        cc_addrs=None,
        subject="Your quote from ACME",
        sent_at=datetime.utcnow(),
        snippet="Here is your quote",
        raw_hash=None,
    )
    db.add(email)
    db.flush()

    db.add(
        EmailBody(
            email_id=email.id,
            mime_type="text/plain",
            charset="utf-8",
            body_text=BODY_TEXT,
            body_html=None,
            body_hash=None,
        )
    )

    db.commit()
    return int(email.id)


def _fake_extract_quote_json(*, subject: str, from_: str | None, to: list[str] | None, date: str | None,
                             body_text: str, attachments_text: str | None) -> Dict[str, Any]:
    # Deterministic, minimal extraction resembling the real schema
    return {
        "vendor": {"name": "ACME Inc", "domain": "acme.com"},
        "versions": [
            {
                "version_label": "v1",
                "currency": "USD",
                "subtotal": 450.0,
                "tax": 45.0,
                "shipping": 10.0,
                "total": 505.0,
                "valid_till": "2030-01-31",
                "terms": "Net 15",
                "items": [
                    {"sku": None, "description": "Widget A", "quantity": 2, "unit_price": 100.0, "discount": 0},
                    {"sku": None, "description": "Widget B", "quantity": 1, "unit_price": 250.0, "discount": 0},
                ],
            }
        ],
    }


def main() -> None:
    db = SessionLocal()
    try:
        email_id = seed_email(db)

        # Monkeypatch LLM call to avoid network and API key requirements
        original = llm_module.extract_quote_json
        llm_module.extract_quote_json = _fake_extract_quote_json  # type: ignore[assignment]
        try:
            result = process_email(db, email_id)
        finally:
            llm_module.extract_quote_json = original  # type: ignore[assignment]

        print({"seed_email_id": email_id, **result})
    finally:
        db.close()


if __name__ == "__main__":
    main()

