from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    gmail_thread_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    last_history_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    emails: Mapped[List[Email]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]
    quotes: Mapped[List[Quote]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[Optional[int]] = mapped_column(ForeignKey("threads.id", ondelete="SET NULL"))
    gmail_message_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    from_addr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    to_addrs: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    cc_addrs: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[Optional[Thread]] = relationship(back_populates="emails")
    bodies: Mapped[List[EmailBody]] = relationship(
        back_populates="email", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]
    attachments: Mapped[List[Attachment]] = relationship(
        back_populates="email", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]
    quote_versions: Mapped[List[QuoteVersion]] = relationship(
        back_populates="source_email"
    )  # type: ignore[name-defined]
    anchored_quote: Mapped[Optional[Quote]] = relationship(
        back_populates="anchor_email", uselist=False
    )  # type: ignore[name-defined]


class EmailBody(Base):
    __tablename__ = "email_bodies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    charset: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    email: Mapped[Email] = relationship(back_populates="bodies")  # type: ignore[name-defined]


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    email: Mapped[Email] = relationship(back_populates="attachments")  # type: ignore[name-defined]


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    quotes: Mapped[List[Quote]] = relationship(back_populates="vendor")  # type: ignore[name-defined]


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[Optional[int]] = mapped_column(ForeignKey("threads.id", ondelete="SET NULL"))
    vendor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    anchor_email_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("emails.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[Optional[Thread]] = relationship(back_populates="quotes")
    vendor: Mapped[Optional[Vendor]] = relationship(back_populates="quotes")
    anchor_email: Mapped[Optional[Email]] = relationship(back_populates="anchored_quote")
    versions: Mapped[List[QuoteVersion]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class QuoteVersion(Base):
    __tablename__ = "quote_versions"
    __table_args__ = (
        UniqueConstraint("quote_id", "source_email_id", name="uq_quote_source_email"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"))
    source_email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    version_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    subtotal: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    tax: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    shipping: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    total: Mapped[float] = mapped_column(Numeric, nullable=False)
    valid_till: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote: Mapped[Quote] = relationship(back_populates="versions")  # type: ignore[name-defined]
    source_email: Mapped[Email] = relationship(back_populates="quote_versions")  # type: ignore[name-defined]
    items: Mapped[List[QuoteItem]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_version_id: Mapped[int] = mapped_column(
        ForeignKey("quote_versions.id", ondelete="CASCADE")
    )
    sku: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    discount: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    line_total: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)

    version: Mapped[QuoteVersion] = relationship(back_populates="items")  # type: ignore[name-defined]

