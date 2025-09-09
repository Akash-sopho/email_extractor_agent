from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class QuoteItem(BaseModel):
    sku: str | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal | None = None
    line_total: Decimal | None = None


class QuoteVersion(BaseModel):
    id: int | None = None
    version_label: str
    currency: str
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    shipping: Decimal | None = None
    total: Decimal
    valid_till: date | None = None
    terms: str | None = None
    items: list[QuoteItem]


class QuoteResponse(BaseModel):
    id: int
    vendor: str | None = None
    thread_id: int
    versions: list[QuoteVersion]


class ThreadResponse(BaseModel):
    id: int
    gmail_thread_id: str
    first_seen_at: str | None = None
    last_synced_at: str | None = None


class VendorResponse(BaseModel):
    id: int
    name: str | None = None
    domain: str | None = None
