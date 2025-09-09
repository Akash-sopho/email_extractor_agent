import json

from jsonschema import Draft202012Validator

from app.extract.prompts import STRICT_JSON_SCHEMA


def test_schema_accepts_minimal_valid_payload():
    Draft202012Validator.check_schema(STRICT_JSON_SCHEMA)
    data = {
        "vendor": {"name": "Acme"},
        "versions": [
            {
                "version_label": "v1",
                "currency": "USD",
                "items": [
                    {"description": "Widget", "quantity": 1, "unit_price": 9.99}
                ],
                "total": 9.99,
            }
        ],
    }
    Draft202012Validator(STRICT_JSON_SCHEMA).validate(data)

