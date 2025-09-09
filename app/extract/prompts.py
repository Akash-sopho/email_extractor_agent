"""Prompt templates and JSON schema for LLM extraction."""

SYSTEM_PROMPT = (
    "You are an information extraction engine. Given a vendor quote email, "
    "output strictly valid JSON adhering to the provided JSON Schema. Never include prose."
)

EXTRACTION_USER_PROMPT = """
Extract ALL quote versions present in the following email.
Return STRICT JSON conforming to the provided schema.
If information is missing, use null rather than guessing.

Email:
Subject: {subject}
From: {from_}
To: {to}
Date: {date}

Body (plaintext):
{body_text}

{attachments_block}
"""

# JSON Schema based on §8
STRICT_JSON_SCHEMA: dict = {
    "type": "object",
    "required": ["vendor", "versions"],
    "properties": {
        "vendor": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "domain": {"type": "string"},
            },
        },
        "versions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["version_label", "currency", "items", "total"],
                "properties": {
                    "version_label": {"type": "string"},
                    "valid_till": {"type": ["string", "null"], "format": "date"},
                    "currency": {"type": "string"},
                    "subtotal": {"type": ["number", "null"]},
                    "tax": {"type": ["number", "null"]},
                    "shipping": {"type": ["number", "null"]},
                    "total": {"type": "number"},
                    "terms": {"type": ["string", "null"]},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["description", "quantity", "unit_price"],
                            "properties": {
                                "sku": {"type": ["string", "null"]},
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "discount": {"type": ["number", "null"]},
                                "line_total": {"type": ["number", "null"]},
                            },
                        },
                    },
                },
            },
        },
    },
}

