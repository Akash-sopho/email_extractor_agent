from decimal import Decimal

from app.extract.normalize import normalize_extraction


def test_normalize_computes_line_totals_and_subtotals():
    data = {
        "vendor": {"name": "ACME"},
        "versions": [
            {
                "version_label": "v1",
                "currency": "USD",
                "items": [
                    {"description": "A", "quantity": 2, "unit_price": 10},
                    {"description": "B", "quantity": 1, "unit_price": 5, "discount": 1},
                ],
                "tax": 2,
                "shipping": 3,
            }
        ],
    }

    out = normalize_extraction(data)
    v = out["versions"][0]
    # line totals
    assert v["items"][0]["line_total"] == 20.0
    assert v["items"][1]["line_total"] == 4.0
    # subtotal = 24, total = 24 + 2 + 3 = 29
    assert v["subtotal"] == 24.0
    assert v["total"] == 29.0

