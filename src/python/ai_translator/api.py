import os
import logging
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mailbills/interpret", tags=["mailbills"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"


class MailBillsInterpretRequest(BaseModel):
    ocr_text: str = Field(..., description="Raw OCR text from the bill or mail")
    source_lang: str = Field("en", description="Language of the OCR text, e.g. 'en' or 'es'")
    target_lang: str = Field("es", description="Target language for the explanation/summary")
    country: Optional[str] = Field(
        default="US",
        description="Country context for bill formats, e.g. 'US', 'MX', etc.",
    )
    bill_type: Optional[str] = Field(
        default=None,
        description="Optional hint: 'electric', 'water', 'phone', 'generic', etc.",
    )


class FieldValue(BaseModel):
    value: str = ""
    confidence: float = 0.0


class MailBillsInterpretResponse(BaseModel):
    ok: bool = True
    summary_en: str = ""
    summary_translated: str = ""
    fields: Dict[str, FieldValue] = Field(
        default_factory=dict,
        description="Key fields extracted from the document (amount_due, due_date, etc.)",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Optional explanation of how the model interpreted the document.",
    )
    error: Optional[str] = None


async def _call_openai_agent(prompt: str) -> Dict[str, Any]:
    """
    Low-level call to OpenAI Chat Completions.
    We use httpx directly so we don't depend on the openai SDK.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # We ask the model to return STRICT JSON, no extra commentary.
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that extracts key fields from utility bills "
                    "and postal mail and explains them clearly to non-native speakers. "
                    "Always respond with STRICT JSON that matches the requested schema, "
                    "with no extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected OpenAI response: %s", data)
        raise RuntimeError(f"Unexpected OpenAI response structure: {exc}") from exc

    try:
        parsed = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse model JSON: %s", content)
        raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc

    return parsed


def _build_prompt(payload: MailBillsInterpretRequest) -> str:
    """
    Build a clear prompt telling the model EXACTLY which JSON keys to return.
    """
    # We fix the expected JSON schema explicitly:
    schema_hint = """
Return a JSON object with this exact structure:

{
  "summary_en": "string, short friendly explanation of the bill in English",
  "summary_translated": "string, same explanation in the target language",
  "fields": {
    "amount_due":   {"value": "string", "confidence": 0.0},
    "due_date":     {"value": "string", "confidence": 0.0},
    "account_number": {"value": "string", "confidence": 0.0},
    "sender":       {"value": "string", "confidence": 0.0},
    "service_address": {"value": "string", "confidence": 0.0}
  },
  "reasoning": "optional: short explanation of how you found the fields"
}

- 'confidence' should be a number between 0 and 1.
- If you are not sure about a field, leave value as an empty string and confidence near 0.
"""

    bill_context = f"Country: {payload.country or 'unknown'}, bill_type: {payload.bill_type or 'unknown'}."
    lang_context = (
        f"The OCR text appears to be in '{payload.source_lang}'. "
        f"The user wants explanations in target_lang='{payload.target_lang}'."
    )

    return (
        f"{schema_hint}\n\n"
        f"{bill_context}\n{lang_context}\n\n"
        "Here is the OCR text from the bill or mail:\n\n"
        f"{payload.ocr_text}"
    )


import json  # keep import here so we don't forget it at the top


@router.post("/interpret", response_model=MailBillsInterpretResponse)
async def interpret_mailbills(payload: MailBillsInterpretRequest) -> MailBillsInterpretResponse:
    """
    Deep agent endpoint:
    - Takes OCR text + context
    - Calls OpenAI
    - Returns structured fields + summaries
    """
    if OFFLINE_MODE:
        # Helpful offline stub so your app doesn't explode in local dev.
        return MailBillsInterpretResponse(
            ok=True,
            summary_en="Offline mode: no real interpretation.",
            summary_translated="Modo sin conexión: sin interpretación real.",
            fields={
                "amount_due": FieldValue(value="", confidence=0.0),
                "due_date": FieldValue(value="", confidence=0.0),
                "account_number": FieldValue(value="", confidence=0.0),
                "sender": FieldValue(value="", confidence=0.0),
                "service_address": FieldValue(value="", confidence=0.0),
            },
            reasoning="OFFLINE_MODE=true stub.",
        )

    if not payload.ocr_text.strip():
        raise HTTPException(status_code=400, detail="ocr_text is empty.")

    prompt = _build_prompt(payload)
    try:
        raw = await _call_openai_agent(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenAI call failed: %s", exc)
        return MailBillsInterpretResponse(
            ok=False,
            error=f"OpenAI call failed: {exc}",
        )

    # Normalize fields into FieldValue objects
    fields_raw = raw.get("fields", {}) if isinstance(raw, dict) else {}
    normalized_fields: Dict[str, FieldValue] = {}

    for key in ["amount_due", "due_date", "account_number", "sender", "service_address"]:
        item = fields_raw.get(key, {}) if isinstance(fields_raw, dict) else {}
        value = item.get("value", "") if isinstance(item, dict) else ""
        confidence = item.get("confidence", 0.0) if isinstance(item, dict) else 0.0
        normalized_fields[key] = FieldValue(value=value or "", confidence=float(confidence or 0.0))

    return MailBillsInterpretResponse(
        ok=True,
        summary_en=raw.get("summary_en", ""),
        summary_translated=raw.get("summary_translated", ""),
        fields=normalized_fields,
        reasoning=raw.get("reasoning"),
    )
