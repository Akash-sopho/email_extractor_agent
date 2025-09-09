from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.extract import pipeline as pipeline_mod


class DummyDB:
    def commit(self):
        pass


class DummyEmailBody(SimpleNamespace):
    pass


class DummyAttachment(SimpleNamespace):
    pass


class DummyEmail(SimpleNamespace):
    pass


def make_dummy_email(tmp_path: Path) -> DummyEmail:
    txt_path = tmp_path / "quote.txt"
    txt_path.write_text("item	2	10.00\n")
    bodies = [
        DummyEmailBody(mime_type="text/plain", body_text="Here is our quote", body_html=None),
        DummyEmailBody(mime_type="text/html", body_text=None, body_html="<p>Quote</p>"),
    ]
    atts = [DummyAttachment(local_path=str(txt_path), filename="quote.txt")]
    return DummyEmail(
        id=1,
        thread_id=1,
        subject="Quotation for services",
        from_addr="vendor@example.com",
        to_addrs=["me@example.com"],
        sent_at=None,
        bodies=bodies,
        attachments=atts,
    )


@pytest.fixture()
def mock_pipeline(monkeypatch, tmp_path):
    email = make_dummy_email(tmp_path)

    def fake_get_email_with_parts(db, email_id: int):
        assert email_id == 1
        return email

    def fake_extract_quote_json(**kwargs):
        return {
            "vendor": {"name": "Vendor Inc.", "domain": "example.com"},
            "versions": [
                {
                    "version_label": "v1",
                    "currency": "USD",
                    "items": [
                        {"description": "Service A", "quantity": 2, "unit_price": 10.0}
                    ],
                    "tax": 0.0,
                    "shipping": 0.0,
                    "total": 20.0,
                }
            ],
        }

    def fake_upsert_vendor(db, name, domain):
        assert name == "Vendor Inc."
        return 42

    class DummyQuote(SimpleNamespace):
        pass

    def fake_get_or_create_quote(db, thread_id, vendor_id, anchor_email_id):
        assert vendor_id == 42
        return DummyQuote(id=7)

    class DummyVersion(SimpleNamespace):
        pass

    def fake_get_or_create_version(db, **kwargs):
        assert kwargs["quote_id"] == 7
        return DummyVersion(id=99)

    created_items = []

    def fake_replace_items(db, version_id, items):
        created_items.extend(items)

    monkeypatch.setattr(pipeline_mod, "get_email_with_parts", fake_get_email_with_parts)
    monkeypatch.setattr(pipeline_mod, "extract_quote_json", fake_extract_quote_json)
    monkeypatch.setattr(pipeline_mod, "upsert_vendor", fake_upsert_vendor)
    monkeypatch.setattr(pipeline_mod, "get_or_create_quote", fake_get_or_create_quote)
    monkeypatch.setattr(pipeline_mod, "get_or_create_version", fake_get_or_create_version)
    monkeypatch.setattr(pipeline_mod, "replace_items", fake_replace_items)

    return email, created_items


def test_process_email_happy_path(mock_pipeline):
    email, created_items = mock_pipeline
    db = DummyDB()
    out = pipeline_mod.process_email(db, 1)
    assert out["processed"] is True
    assert out["versions"] == 1
    assert len(created_items) == 1
    assert created_items[0]["description"] == "Service A"

