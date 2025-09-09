"""Quotes CRUD functions for listing and upserts."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Quote, QuoteItem, QuoteVersion


def list_quotes(db: Session) -> list[Quote]:
    return db.query(Quote).all()


def get_quote(db: Session, quote_id: int) -> Optional[Quote]:
    return db.query(Quote).filter(Quote.id == quote_id).one_or_none()


def get_or_create_quote(db: Session, thread_id: int | None, vendor_id: int | None, anchor_email_id: int | None) -> Quote:
    q = db.query(Quote).filter(Quote.thread_id == thread_id, Quote.vendor_id == vendor_id)
    quote = q.one_or_none()
    if quote is None:
        quote = Quote(thread_id=thread_id, vendor_id=vendor_id, anchor_email_id=anchor_email_id, status="active")
        db.add(quote)
        db.flush()
    else:
        if anchor_email_id and quote.anchor_email_id is None:
            quote.anchor_email_id = anchor_email_id
    return quote


def get_or_create_version(
    db: Session,
    *,
    quote_id: int,
    source_email_id: int,
    version_label: str | None,
    currency: str,
    subtotal: float | None,
    tax: float | None,
    shipping: float | None,
    total: float,
    valid_till,
    terms: str | None,
    extracted_json: dict | None,
) -> QuoteVersion:
    v = (
        db.query(QuoteVersion)
        .filter(QuoteVersion.quote_id == quote_id, QuoteVersion.source_email_id == source_email_id)
        .one_or_none()
    )
    if v is None:
        v = QuoteVersion(
            quote_id=quote_id,
            source_email_id=source_email_id,
            version_label=version_label,
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=total,
            valid_till=valid_till,
            terms=terms,
            extracted_json=extracted_json,
        )
        db.add(v)
        db.flush()
    else:
        # Optionally update fields on reprocess
        v.version_label = version_label
        v.currency = currency
        v.subtotal = subtotal
        v.tax = tax
        v.shipping = shipping
        v.total = total
        v.valid_till = valid_till
        v.terms = terms
        v.extracted_json = extracted_json
        db.flush()
    return v


def replace_items(db: Session, version_id: int, items: list[dict]) -> None:
    db.query(QuoteItem).filter(QuoteItem.quote_version_id == version_id).delete()
    for it in items:
        db.add(
            QuoteItem(
                quote_version_id=version_id,
                sku=it.get("sku"),
                description=it.get("description"),
                quantity=it.get("quantity"),
                unit_price=it.get("unit_price"),
                discount=it.get("discount"),
                line_total=it.get("line_total"),
            )
        )
    db.flush()

