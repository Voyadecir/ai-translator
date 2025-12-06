import json
import logging
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Router for all mail & bills endpoints
# Final path = /api/mailbills/interpret (because api.py adds prefix="/api")
router = APIRouter(prefix="/mailbills", tags=["mailbills"])

logger = logging.getLogger("mailbills_agent")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


# ---------- Pydantic models ----------


class MailBillsRequest(BaseModel):
    """
    Request from the frontend deep-agent caller.

    NOTE: This matches mailbills.js callInterpret:
      { ocr_text, locale: "en-US" | "es-MX", document_kind: "utility_bill" | ... }
    """
    ocr_text: str = Field(..., description="Full OCR text from Azure OCR.")
    locale: str = Field(
        "en-US",
        description="BCP-47 locale like en-US or es-MX; used for translated summary.",
    )
    document_kind: str = Field(
        "utility_bill",
        description="High-level kind: utility_bill, tax_notice, bank_statement, generic_mail, etc.",
    )


class OtherAmount(BaseModel):
    """Any extra amounts on the bill."""
    label: str = Field(
        ...,
        description="Short label like 'Park total', 'Previous balance', 'Unmetered amount due'.",
    )
    value: Optional[float] = Field(
        None,
        description="Numeric amount if you can parse it, otherwise null.",
    )
    raw_text: Optional[str] = Field(
        None,
        description="Original text fragment, if helpful.",
    )


class PaymentOption(BaseModel):
    """How to pay: from bank, by card, by check, etc."""
    method: str = Field(
        ...,
        description="One of: bank, card, check, online_portal, phone, other.",
    )
    label: Optional[str] = Field(
        None,
        description="Short human label like 'Pay from your bank account'.",
    )
    details: Optional[str] = Field(
        None,
        description="1–2 short sentences describing how to use this payment method.",
    )


class MailBillsFields(BaseModel):
    """
    Structured fields extracted from the mail/bill.

    amount_due_main:
        Primary amount the *recipient* personally owes now.
    amount_due_secondary:
        A second clearly distinct amount (e.g. park total, unmetered amount).
    amount_due:
        Legacy mirror of amount_due_main so older JS can still use it.
    """
    amount_due_main: Optional[float] = Field(
        None,
        description="Primary amount the recipient personally owes now.",
    )
    amount_due_label: Optional[str] = Field(
        None,
        description="Label like 'Amount Due', 'Amount Past Due', 'Total Amount You Owe'.",
    )
    amount_due_secondary: Optional[float] = Field(
        None,
        description="Second amount due if the bill clearly has two.",
    )
    amount_due: Optional[float] = Field(
        None,
        description="Legacy mirror of amount_due_main for older frontends.",
    )

    due_date: Optional[str] = Field(
        None,
        description="Due date or 'pay by' date as simple text.",
    )
    account_number: Optional[str] = None
    sender: Optional[str] = None
    service_address: Optional[str] = None

    identity_requirements: List[str] = Field(
        default_factory=list,
        description="Short bullet list, e.g. 'Bank account number', 'Routing number', 'Filing status'.",
    )

    payment_options: List[PaymentOption] = Field(
        default_factory=list,
        description="Ways to pay (bank, card, check, online portal, phone, other).",
    )

    other_amounts: List[OtherAmount] = Field(
        default_factory=list,
        description="Any additional important dollar amounts with labels.",
    )


class MailBillsResponse(BaseModel):
    ok: bool
    message: str
    detected_language: Optional[str] = None
    summary_en: Optional[str] = None
    summary_translated: Optional[str] = None
    fields: MailBillsFields


# ---------- OpenAI helper ----------


async def _call_openai_chat(system_prompt: str, user_prompt: str) -> dict:
    """Low-level HTTP call to OpenAI Chat Completions with JSON response_format."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured in the environment.")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": OPENAI_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
        )

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Log the first chunk of the body for debugging
        text_preview = e.response.text[:500]
        logger.error("OpenAI HTTP error %s: %s", e.response.status_code, text_preview)
        raise

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def _build_system_prompt() -> str:
    """System prompt telling the model exactly what JSON to emit."""
    return """
You are an assistant that reads mail and bills for people who may not speak English fluently.

Your job:
- Read OCR text from utility bills, IRS-style tax notices, bank/credit letters, and other mail.
- Carefully identify what the recipient personally owes now, what they must do, and by when.
- Extract structured fields and short summaries so a human can understand quickly.

You MUST return a SINGLE JSON object of this exact shape:

{
  "detected_language": string | null,
  "summary_en": string | null,
  "summary_translated": string | null,
  "fields": {
    "amount_due_main": number | null,
    "amount_due_label": string | null,
    "amount_due_secondary": number | null,
    "amount_due": number | null,
    "due_date": string | null,
    "account_number": string | null,
    "sender": string | null,
    "service_address": string | null,
    "identity_requirements": string[],
    "payment_options": [
      {
        "method": "bank" | "card" | "check" | "online_portal" | "phone" | "other",
        "label": string | null,
        "details": string | null
      }
    ],
    "other_amounts": [
      {
        "label": string,
        "value": number | null,
        "raw_text": string | null
      }
    ]
  }
}

CRITICAL rules:

- Treat this like a real bill or official letter. Avoid guessing.
- "amount_due_main" is the amount the RECIPIENT personally owes now.
  - On utility bills, use the final "Amount Due" / "Total Due" for the customer.
  - On tax letters (e.g. IRS CP503), use the main "Amount You Owe" or "Amount Past Due".
- When there is a smaller line item (like "Commodity Charge = 44.33") AND a final
  "Amount Due = 47.00", you MUST use the final amount as amount_due_main.
- If there is a clearly different second amount (like a park-wide total or
  unmetered total due), put it in amount_due_secondary or in other_amounts with
  a clear label.
- Keep "amount_due" as a mirror of amount_due_main so older software can still use it.

- "identity_requirements":
  - Short bullet list of what the person needs to provide: e.g.
    "Bank account number", "Routing number", "Filing status", "Address".
  - Use plain, simple language.

- "payment_options":
  - Group ways to pay into:
    bank, card, check, online_portal, phone, other.
  - For each, provide:
    - method
    - label (short name, e.g. "Pay from your bank account")
    - details (1–2 short sentences).

- "other_amounts":
  - Include any important dollar amounts that aren't the main amount due:
    park totals, previous balances, unmetered space totals, penalties, etc.
  - Give each a label and, if possible, a numeric value.

- "summary_en":
  - 2–4 short sentences in English explaining:
    - What this document is
    - What the person owes (if anything)
    - Any deadline and what action they should take.

- "summary_translated":
  - If the locale is not English, write a similarly short summary in that language.
  - If the locale is English, you may leave summary_translated null or repeat summary_en.

Return ONLY valid JSON. Do NOT include any explanation or commentary outside the JSON.
""".strip()


def _build_user_prompt(payload: MailBillsRequest) -> str:
    """User prompt with locale and raw OCR text."""
    return f"""
Locale: {payload.locale}
Document kind: {payload.document_kind}

Here is the full OCR text of the document:

\"\"\"{payload.ocr_text}\"\"\"
""".strip()


# ---------- Response builder ----------


def _build_response_from_llm(parsed: dict) -> MailBillsResponse:
    """
    Defensive parsing: make sure we always return a valid MailBillsResponse,
    even if the model forgot some keys.
    """
    detected_language = parsed.get("detected_language")
    summary_en = parsed.get("summary_en") or parsed.get("summary") or ""
    summary_translated = parsed.get("summary_translated") or ""

    fields_dict = parsed.get("fields") or {}
    fields = MailBillsFields(**fields_dict)

    # Legacy mirror: if amount_due not set but main is, copy it
    if fields.amount_due is None and fields.amount_due_main is not None:
        fields.amount_due = fields.amount_due_main

    return MailBillsResponse(
        ok=True,
        message="Mail & bills interpretation succeeded.",
        detected_language=detected_language,
        summary_en=summary_en,
        summary_translated=summary_translated,
        fields=fields,
    )


# ---------- FastAPI endpoint ----------


@router.post("/interpret", response_model=MailBillsResponse)
async def interpret_mailbills(req: MailBillsRequest) -> MailBillsResponse:
    """
    Deep-agent endpoint:
    - Takes OCR text + locale + document kind.
    - Calls OpenAI to extract fields and summaries.
    - Returns structured JSON for the frontend.
    """
    try:
        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(req)
        parsed = await _call_openai_chat(system_prompt, user_prompt)
        return _build_response_from_llm(parsed)
    except Exception as exc:  # noqa: BLE001
        logger.exception("mailbills/interpret failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": "Failed to interpret mail/bill."},
        ) from exc
