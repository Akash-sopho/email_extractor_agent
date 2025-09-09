"""Normalization and validation of extraction JSON."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable, MutableMapping, Any


def _to_decimal(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def compute_line_total(quantity: Decimal, unit_price: Decimal, discount: Decimal | None) -> Decimal:
    total = quantity * unit_price
    if discount:
        total -= discount
    return total


def sum_totals(values: Iterable[Decimal]) -> Decimal:
    s = Decimal("0")
    for v in values:
        s += v
    return s


def normalize_extraction(data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    versions = data.get("versions") or []
    for v in versions:
        items = v.get("items") or []
        dec_items: list[Decimal] = []
        for it in items:
            q = _to_decimal(it.get("quantity")) or Decimal("0")
            p = _to_decimal(it.get("unit_price")) or Decimal("0")
            d = _to_decimal(it.get("discount"))
            lt = compute_line_total(q, p, d)
            it["line_total"] = float(lt)
            dec_items.append(lt)

        subtotal = _to_decimal(v.get("subtotal"))
        if subtotal is None:
            subtotal = sum_totals(dec_items)
            v["subtotal"] = float(subtotal)

        tax = _to_decimal(v.get("tax")) or Decimal("0")
        shipping = _to_decimal(v.get("shipping")) or Decimal("0")
        total = _to_decimal(v.get("total"))
        if total is None:
            total = subtotal + tax + shipping
            v["total"] = float(total)
    return data

