"""OpenAI call and JSON Schema validation for extraction."""

from __future__ import annotations

import json
from typing import Any, Dict

from jsonschema import Draft202012Validator
from openai import OpenAI

from app.core.config import get_settings
from app.extract.prompts import SYSTEM_PROMPT, EXTRACTION_USER_PROMPT, STRICT_JSON_SCHEMA


validator = Draft202012Validator(STRICT_JSON_SCHEMA)


def _build_user_prompt(subject: str, from_: str | None, to: list[str] | None, date: str | None,
                       body_text: str, attachments_text: str | None) -> str:
    attachments_block = ""
    if attachments_text:
        attachments_block = "\nAttachments (plaintext excerpts):\n" + attachments_text
    return EXTRACTION_USER_PROMPT.format(
        subject=subject or "",
        from_=from_ or "",
        to=", ".join(to or []) or "",
        date=date or "",
        body_text=body_text or "",
        attachments_block=attachments_block,
    )


def extract_quote_json(*, subject: str, from_: str | None, to: list[str] | None, date: str | None,
                       body_text: str, attachments_text: str | None) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        # No API key configured: return empty extraction to keep pipeline idempotent
        return {"vendor": {"name": None}, "versions": []}
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    user_prompt = _build_user_prompt(subject, from_, to, date, body_text, attachments_text)

    try:
        # Prefer Responses API if available, else fallback to Chat Completions
        content = None
        try:
            resp = client.responses.create(
                model="gpt-4.1-mini",
                temperature=0.1,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "input_text", "text": json.dumps(STRICT_JSON_SCHEMA)},
                    ]},
                ],
            )
            content = resp.output_text
        except Exception:
            chat = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": user_prompt + "\n\nJSON Schema:\n" + json.dumps(STRICT_JSON_SCHEMA),
                    },
                ],
            )
            content = chat.choices[0].message.content if chat.choices else None

        if not content:
            raise RuntimeError("Empty response from LLM")

        # Parse strict JSON
        data = json.loads(content)
    except Exception as e:
        # On failure, return safe baseline structure
        data = {"vendor": {"name": None}, "versions": []}

    # Validate and coerce types where possible
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        # Best-effort: if invalid, still return data but ensure required keys exist
        data.setdefault("vendor", {}).setdefault("name", None)
        data.setdefault("versions", [])
    return data
