import os
import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

# Router for all mail & bills endpoints
router = APIRouter(prefix="/mailbills", tags=["mailbills"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30.0"))


#
# Basic field types
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


class AmountItem(BaseModel):
    label: str = Field("", description="Label of the amount, e.g. 'Total due now'.")
    value: str = Field("", description="Amount text, e.g. '$123.45'.")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence that this line was read correctly.",
    )


class IdentityRequirement(BaseModel):
    label: str = Field(
        "",
        description="Name of the item needed to identify yourself, e.g. 'Account number'.",
    )
    required: bool = Field(
        True,
        description="True if this is clearly required in the document.",
    )
    description: str = Field(
        "",
        description="Short explanation of where to find it or why it's needed.",
    )


class PaymentMethod(BaseModel):
    method_type: str = Field(
        "",
        description="Type of payment, e.g. 'online', 'bank', 'card', 'mail', 'phone', 'in_person'.",
    )
    description: str = Field(
        "",
        description="How to pay using this method, in simple language.",
    )
    url: Optional[str] = Field(
        None,
        description="Website or portal URL, if one is clearly shown.",
    )


class RiskFlag(BaseModel):
    level: str = Field(
        "low",
        description="Rough seriousness: 'low', 'medium', or 'high'.",
    )
    reason: str = Field(
        "",
        description="Short explanation of why this might be important or urgent.",
    )


class FollowupAction(BaseModel):
    label: str = Field(
        "",
        description="Short action name, e.g. 'Call your provider'.",
    )
    description: str = Field(
        "",
        description="Simple explanation of what the person should do next.",
    )


#
# Request/response shapes
#

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

    # New richer structure
    document_type: str = Field(
        "unknown",
        description=(
            "High-level type such as 'utility_bill', 'tax_notice', "
            "'eviction_notice', 'medical_bill', 'traffic_ticket', 'other_info_sheet'."
        ),
    )
    is_template: bool = Field(
        False,
        description="True if this looks like an example / blank form, not a personal bill.",
    )

    amounts: List[AmountItem] = Field(
        default_factory=list,
        description="All amounts the model noticed, including samples or examples.",
    )
    identity_requirements: List[IdentityRequirement] = Field(
        default_factory=list,
        description="Things the document says you need to identify yourself (account number, SSN, etc.).",
    )
    payment_methods: List[PaymentMethod] = Field(
        default_factory=list,
        description="Ways to pay described in the document (online, card, bank, mail, etc.).",
    )
    risk_flags: List[RiskFlag] = Field(
        default_factory=list,
        description="Signals about how serious this might be (late fees, legal risk, etc.).",
    )
    followup_actions: List[FollowupAction] = Field(
        default_factory=list,
        description="Simple suggested next steps based on the document.",
    )


#
# Prompt construction
#

def _build_system_prompt() -> str:
    return (
        "You are an assistant that reads OCR text from utility bills or official letters "
        "in English and Spanish for immigrants and their families. Your job is to:\n"
        "1) Understand what kind of document it is.\n"
        "2) Extract key fields: amount_due, due_date, account_number, sender, service_address.\n"
        "3) List all amounts you see, with labels.\n"
        "4) Describe what identity information is needed (account number, SSN, etc.).\n"
        "5) Describe how the person can pay (online, bank, card, mail, etc.).\n"
        "6) Briefly flag how serious this looks (risk) and simple next steps.\n"
        "7) Write a short summary in English and the same summary + explanation in the target language.\n\n"
        "IMPORTANT:\n"
        "- If the document is clearly a BLANK FORM or SAMPLE (example, template, dotted lines, no real person), "
        "then set is_template=true, leave fields.amount_due empty, and explain that this is only an example.\n"
        "- If there are many amounts, choose the main amount the person must pay now for fields.amount_due, "
        "and put all amounts (examples, fees, totals) inside the 'amounts' list with clear labels.\n\n"
        "You MUST respond with a single valid JSON object only, no extra text, exactly:\n"
        "{\n"
        '  \"detected_language\": \"en\" | \"es\" | \"other\",\n'
        '  \"document_type\": \"utility_bill\" | \"tax_notice\" | \"eviction_notice\" | \"medical_bill\" | '
        '\"traffic_ticket\" | \"other_info_sheet\" | \"other\",\n'
        '  \"is_template\": true | false,\n'
        '  \"summary_en\": \"...\",\n'
        '  \"summary_translated\": \"...\",\n'
        '  \"explanation_translated\": \"...\",\n'
        '  \"fields\": {\n'
        '    \"amount_due\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"due_date\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"account_number\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"sender\": { \"value\": \"...\", \"confidence\": 0.0 },\n'
        '    \"service_address\": { \"value\": \"...\", \"confidence\": 0.0 }\n'
        "  },\n"
        '  \"amounts\": [\n'
        '    { \"label\": \"...\", \"value\": \"...\", \"confidence\": 0.0 }\n'
        "  ],\n"
        '  \"identity_requirements\": [\n'
        '    { \"label\": \"...\", \"required\": true, \"description\": \"...\" }\n'
        "  ],\n"
        '  \"payment_methods\": [\n'
        '    { \"method_type\": \"online\", \"description\": \"...\", \"url\": \"...\" }\n'
        "  ],\n"
        '  \"risk_flags\": [\n'
        '    { \"level\": \"low\" | \"medium\" | \"high\", \"reason\": \"...\" }\n'
        "  ],\n"
        '  \"followup_actions\": [\n'
        '    { \"label\": \"...\", \"description\": \"...\" }\n'
        "  ]\n"
        "}\n\n"
        "If the document does not contain a certain piece of information, use empty strings and empty lists, "
        "and confidence 0.0. Do not invent URLs or ID numbers."
    )


def _build_user_prompt(payload: MailBillsRequest) -> str:
    hint_line = ""
    if payload.bill_hint:
        hint_line = f"Document hint: {payload.bill_hint}\n"

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


#
# OpenAI call
#

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
        raise RuntimeError(
            f"Failed to parse JSON from model output: {e}; content={content!r}"
        ) from e

    return parsed


#
# Response builder
#

def _field_from_dict(name: str, source: dict) -> BillField:
    raw = source.get(name) or {}
    return BillField(
        value=str(raw.get("value") or ""),
        confidence=float(raw.get("confidence") or 0.0),
    )


def _build_response_from_llm(
    payload: MailBillsRequest,
    parsed: dict,
) -> MailBillsResponse:
    detected_language = parsed.get("detected_language") or "unknown"
    summary_en = parsed.get("summary_en") or ""
    summary_translated = parsed.get("summary_translated") or ""
    explanation_translated = parsed.get("explanation_translated") or ""

    fields_raw = parsed.get("fields") or {}
    bill_fields = BillFields(
        amount_due=_field_from_dict("amount_due", fields_raw),
        due_date=_field_from_dict("due_date", fields_raw),
        account_number=_field_from_dict("account_number", fields_raw),
        sender=_field_from_dict("sender", fields_raw),
        service_address=_field_from_dict("service_address", fields_raw),
    )

    def _parse_list(model_cls, key: str):
        items = parsed.get(key) or []
        if not isinstance(items, list):
            return []
        out: List[BaseModel] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                out.append(model_cls(**item))
            except Exception:
                # Be defensive: skip bad entries instead of crashing.
                continue
        return out

    document_type = parsed.get("document_type") or "unknown"
    is_template = bool(parsed.get("is_template") or False)

    amounts = _parse_list(AmountItem, "amounts")
    identity_requirements = _parse_list(IdentityRequirement, "identity_requirements")
    payment_methods = _parse_list(PaymentMethod, "payment_methods")
    risk_flags = _parse_list(RiskFlag, "risk_flags")
    followup_actions = _parse_list(FollowupAction, "followup_actions")

    return MailBillsResponse(
        ok=True,
        message="Mail & bills interpretation succeeded.",
        detected_language=detected_language,
        summary_en=summary_en,
        summary_translated=summary_translated,
        explanation_translated=explanation_translated,
        fields=bill_fields,
        raw_ocr_text=payload.ocr_text,
        document_type=document_type,
        is_template=is_template,
        amounts=amounts,
        identity_requirements=identity_requirements,
        payment_methods=payment_methods,
        risk_flags=risk_flags,
        followup_actions=followup_actions,
    )


#
# Endpoint
#

@router.post("/interpret", response_model=MailBillsResponse)
async def interpret_mailbills(req: MailBillsRequest) -> MailBillsResponse:
    """
    Deep-agent style endpoint: takes OCR text + optional hints,
    calls OpenAI, and returns structured bill info.
    """
    try:
        parsed = await _call_openai_for_mailbills(req)
        return _build_response_from_llm(req, parsed)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc
