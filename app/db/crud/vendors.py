"""Vendors CRUD: upsert by domain/name."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Vendor


def upsert_vendor(db: Session, name: str | None, domain: str | None) -> int:
    q = db.query(Vendor)
    if domain:
        vendor = q.filter(Vendor.domain == domain).one_or_none()
        if vendor:
            if name and not vendor.name:
                vendor.name = name
            db.flush()
            return vendor.id
    # Fallback by name
    if name:
        vendor = db.query(Vendor).filter(Vendor.name == name).one_or_none()
        if vendor:
            if domain and not vendor.domain:
                vendor.domain = domain
            db.flush()
            return vendor.id

    vendor = Vendor(name=name, domain=domain)
    db.add(vendor)
    db.flush()
    return vendor.id

