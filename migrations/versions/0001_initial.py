"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-09-09 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # threads
    op.create_table(
        "threads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("gmail_thread_id", sa.String(), nullable=False, unique=True),
        sa.Column("last_history_id", sa.String(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )

    # emails
    op.create_table(
        "emails",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.BigInteger(), sa.ForeignKey("threads.id", ondelete="SET NULL")),
        sa.Column("gmail_message_id", sa.String(), nullable=False, unique=True),
        sa.Column("from_addr", sa.Text(), nullable=True),
        sa.Column("to_addrs", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("cc_addrs", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("raw_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # email_bodies
    op.create_table(
        "email_bodies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email_id", sa.BigInteger(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("charset", sa.String(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_hash", sa.String(), nullable=True),
    )

    # attachments
    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email_id", sa.BigInteger(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
    )

    # vendors
    op.create_table(
        "vendors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
    )

    # quotes
    op.create_table(
        "quotes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.BigInteger(), sa.ForeignKey("threads.id", ondelete="SET NULL")),
        sa.Column("vendor_id", sa.BigInteger(), sa.ForeignKey("vendors.id", ondelete="SET NULL")),
        sa.Column("anchor_email_id", sa.BigInteger(), sa.ForeignKey("emails.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # quote_versions
    op.create_table(
        "quote_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("quote_id", sa.BigInteger(), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_email_id", sa.BigInteger(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_label", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("subtotal", sa.Numeric(), nullable=True),
        sa.Column("tax", sa.Numeric(), nullable=True),
        sa.Column("shipping", sa.Numeric(), nullable=True),
        sa.Column("total", sa.Numeric(), nullable=False),
        sa.Column("valid_till", sa.Date(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("extracted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("quote_id", "source_email_id", name="uq_quote_source_email"),
    )

    # quote_items
    op.create_table(
        "quote_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "quote_version_id",
            sa.BigInteger(),
            sa.ForeignKey("quote_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit_price", sa.Numeric(), nullable=True),
        sa.Column("discount", sa.Numeric(), nullable=True),
        sa.Column("line_total", sa.Numeric(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("quote_items")
    op.drop_table("quote_versions")
    op.drop_table("quotes")
    op.drop_table("vendors")
    op.drop_table("attachments")
    op.drop_table("email_bodies")
    op.drop_table("emails")
    op.drop_table("threads")

