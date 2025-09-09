from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.security import api_key_auth
from app.db.models import Quote, QuoteItem, QuoteVersion, Vendor, Email
from app.db.session import get_db
from app.schemas.dto import QuoteResponse, QuoteVersion as QuoteVersionDTO, QuoteItem as QuoteItemDTO

router = APIRouter(dependencies=[Depends(api_key_auth)])


def _to_dto(quote: Quote, *, latest_only: bool) -> QuoteResponse:
    versions = sorted(quote.versions, key=lambda v: (v.created_at or v.id))
    if latest_only and versions:
        versions = [versions[-1]]

    dto_versions: list[QuoteVersionDTO] = []
    for v in versions:
        items = [
            QuoteItemDTO(
                sku=i.sku,
                description=i.description or "",
                quantity=i.quantity or 0,  # type: ignore[arg-type]
                unit_price=i.unit_price or 0,  # type: ignore[arg-type]
                discount=i.discount,
                line_total=i.line_total,
            )
            for i in v.items
        ]
        dto_versions.append(
            QuoteVersionDTO(
                id=int(v.id),
                version_label=v.version_label or "",
                currency=v.currency,
                subtotal=v.subtotal,  # type: ignore[arg-type]
                tax=v.tax,  # type: ignore[arg-type]
                shipping=v.shipping,  # type: ignore[arg-type]
                total=v.total,  # type: ignore[arg-type]
                valid_till=v.valid_till,
                terms=v.terms,
                items=items,
            )
        )
    return QuoteResponse(
        id=int(quote.id),
        vendor=quote.vendor.name if quote.vendor else None,
        thread_id=int(quote.thread_id) if quote.thread_id is not None else 0,
        versions=dto_versions,
    )


@router.get("", response_model=list[QuoteResponse])
def list_quotes(
    vendor: Optional[str] = Query(default=None, description="Filter by vendor name (ilike)"),
    date_from: Optional[date] = Query(default=None, description="Filter by source email sent_at >="),
    date_to: Optional[date] = Query(default=None, description="Filter by source email sent_at <="),
    has_latest_only: bool = Query(default=False, description="Return only latest version per quote"),
    db: Session = Depends(get_db),
) -> list[QuoteResponse]:
    q = (
        db.query(Quote)
        .options(joinedload(Quote.vendor), joinedload(Quote.versions).joinedload(QuoteVersion.items))
        .join(Quote.vendor, isouter=True)
        .join(Quote.versions, isouter=True)
        .join(Email, QuoteVersion.source_email)  # join to Email for date filters
    )

    if vendor:
        q = q.filter(func.lower(Vendor.name).like(f"%{vendor.lower()}%"))
    if date_from:
        q = q.filter(func.date(Email.sent_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Email.sent_at) <= date_to)

    quotes = q.distinct(Quote.id).all()
    return [_to_dto(qa, latest_only=has_latest_only) for qa in quotes]


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(quote_id: int, db: Session = Depends(get_db)) -> QuoteResponse:
    q = (
        db.query(Quote)
        .options(joinedload(Quote.vendor), joinedload(Quote.versions).joinedload(QuoteVersion.items))
        .filter(Quote.id == quote_id)
    )
    quote = q.one_or_none()
    if not quote:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Quote not found")
    return _to_dto(quote, latest_only=False)
