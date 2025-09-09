from app.extract.prefilter import likely_contains_quote


def test_likely_contains_quote_subject_keywords():
    assert likely_contains_quote("Request for QUOTE", "") is True
    assert likely_contains_quote("Pricing Proposal", None) is True
    assert likely_contains_quote("Meeting notes", "Pricing table attached") is True
    assert likely_contains_quote("FYI", "hello world") is False

