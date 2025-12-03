import os
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

# Router for all mail & bills endpoints
router = APIRouter(prefix="/mailbills", tags=["mailbills"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


#
# Pydantic models
#

class BillField(BaseModel):
    value: str = Field("", description="Extracted value, or empty string if not found.")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Rough confidence score between 0 and 1.",
    )


class BillFields(BaseModel):
    amount_due: BillField = BillField()
    due_date: BillField = BillField()
    account_number: BillField = BillField()
    sender: BillField = BillField()
    service_address: BillField = BillField()


class MailBillsRequest(BaseModel):
    ocr_text: str = Field(..., min_length=1, description="Full OCR text from Azure.")
    source_lang: str = Field(
        "auto",
        description="Original language: 'auto', 'en', or 'es'.",
    )
    target_lang: str = Field(
        "es",
        description="Target language: typically 'es' or 'en'.",
    )
    bill_hint: Optional[str] = Field(
        None,
        description="Optional hint, e.g. 'electricity bill', 'water bill', 'IRS letter'.",
    )


class MailBillsResponse(BaseModel):
    ok: bool
    message: str
    detected_language: str
    summary_en: str
    summary_translated: str
    explanation_translated: str
    fields: BillFields
    raw_ocr_text: str


#
# Helper: build prompt & call OpenAI
#

def _build_system_prompt() -> str:
    return (
        "You are an assistant that reads OCR text from utility bills or official letters "
        "in English and Spanish. Your job is to:\n"
        "1) Understand the document.\n"
        "2) Extract key fields: amount_due, due_date, account_number, sender, service_address.\n"
        "3) Write a short summary in English.\n"
        "4) Write the same summary and a simple explanation in the target language.\n\n"
        "You MUST respond with a single valid JSON object only, no extra text, exactly:\n"
        "{\n"
        '  \"detected_language\": \"en\" | \"es\" | \"other\",\n'
        '  \"summary_en\": \"...\",\n'
        '  \"summary_translated\": \"...\",\n'
        '  \"explanation_translated\": \"...\",\n'
        '  \"fields\": {\n'
        '    \"amount_due\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"due_date\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"account_number\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"sender\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"service_address\": { \"value\": \"...\", \"confidence\": 0.0 }\n'
        "  }\n"
        "}\n\n"
        "If a field is missing, use an empty string and confidence 0.0. "
        "Dates should be in ISO format when possible (YYYY-MM-DD). "
        "Amounts should include currency symbols if present."
    )


def _build_user_prompt(payload: MailBillsRequest) -> str:
    hint_line = ""
    if payload.bill_hint:
        hint_line = f"Document hint: {payload.bill_hint}\n"

    # Keep it simple but clear
    return (
        f"Source language preference: {payload.source_lang}\n"
        f"Target language: {payload.target_lang}\n"
        f"{hint_line}"
        "Here is the OCR text from a bill or letter:\n"
        "----- OCR START -----\n"
        f"{payload.ocr_text}\n"
        "----- OCR END -----\n"
        "Remember: respond ONLY with the JSON object described by the system message."
    )


async def _call_openai_for_mailbills(payload: MailBillsRequest) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured in the environment.")

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(payload)},
    ]

    req_json = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=req_json,
        )

    if resp.status_code >= 300:
        raise RuntimeError(
            f"OpenAI API error {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Unexpected OpenAI response shape: {e}") from e

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        # Model didn't strictly follow instructions
        raise RuntimeError(f"Failed to parse JSON from model output: {e}; content={content!r}") from e

    return parsed


def _build_response_from_llm(
    payload: MailBillsRequest,
    parsed: dict,
) -> MailBillsResponse:
    # Safety: pull fields with defaults so we never crash the UI
    detected_language = parsed.get("detected_language") or "unknown"
    summary_en = parsed.get("summary_en") or ""
    summary_translated = parsed.get("summary_translated") or ""
    explanation_translated = parsed.get("explanation_translated") or ""

    fields_raw = parsed.get("fields") or {}
    # Each subfield is a dict with value/confidence; default if missing
    def _field(name: str) -> BillField:
        raw = fields_raw.get(name) or {}
        return BillField(
            value=str(raw.get("value") or ""),
            confidence=float(raw.get("confidence") or 0.0),
        )

    bill_fields = BillFields(
        amount_due=_field("amount_due"),
        due_date=_field("due_date"),
        account_number=_field("account_number"),
        sender=_field("sender"),
        service_address=_field("service_address"),
    )

    return MailBillsResponse(
        ok=True,
        message="Mail & bills interpretation succeeded.",
        detected_language=detected_language,
        summary_en=summary_en,
        summary_translated=summary_translated,
        explanation_translated=explanation_translated,
        fields=bill_fields,
        raw_ocr_text=payload.ocr_text,
    )


#
# FastAPI endpoint
#

@router.post("/interpret", response_model=MailBillsResponse)
async def interpret_mailbills(req: MailBillsRequest) -> MailBillsResponse:
    """
    Deep-agent style endpoint:
    Takes OCR text + optional hints, calls OpenAI, and returns structured bill info.
    """
    try:
        parsed = await _call_openai_for_mailbills(req)
        return _build_response_from_llm(req, parsed)
    except Exception as exc:  # noqa: BLE001
        # Log-style error; FastAPI will still send JSON error
        # (In a real app you'd use logging.)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc
