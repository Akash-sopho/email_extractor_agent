"""Quote detection heuristic placeholder (Task D)."""


def likely_contains_quote(subject: str, body_text: str | None) -> bool:
    keywords = [
        "quote",
        "quotation",
        "proposal",
        "estimate",
        "pricing",
        "proforma",
        "invoice",
    ]
    text = f"{subject}\n{body_text or ''}".lower()
    return any(k in text for k in keywords)

