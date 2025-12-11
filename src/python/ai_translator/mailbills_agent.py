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
      description=(
          "Type of payment, e.g. 'online', 'bank', 'card', 'mail', "
          "'phone', 'in_person'."
      ),
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
  # Let the model auto-detect, but we still record the user's intent.
  source_lang: str = Field(
      "auto",
      description="Original language: 'auto', 'en', or 'es'.",
  )
  # This is what YOU choose in the UI: Spanish or English explanation.
  target_lang: str = Field(
      "es",
      description="Target language for the explanation: typically 'es' or 'en'.",
  )
  bill_hint: Optional[str] = Field(
      None,
      description=(
          "Optional hint, e.g. 'electricity bill', 'water bill', "
          "'IRS letter', 'hospital letter', 'school letter', 'work notice', "
          "'auto policy', 'rental contract'."
      ),
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

  # High-level doc classification
  document_type: str = Field(
      "unknown",
      description=(
          "High-level type such as 'utility_bill', 'bank_statement', "
          "'credit_card_statement', 'loan_statement', 'medical_bill', "
          "'tax_form', 'tax_notice', 'insurance_policy', 'auto_policy', "
          "'investment_statement', 'receipt', 'court_notice', 'legal_notice', "
          "'contract', 'lease_agreement', 'rental_agreement', 'eviction_notice', "
          "'traffic_ticket', 'government_letter', 'benefit_letter', 'voter_mail', "
          "'license_id_mail', 'census_or_survey', 'school_letter', 'work_letter', "
          "'payroll_document', 'hr_letter', 'personal_letter', 'greeting_card', "
          "'magazine_or_newspaper', 'catalog_or_flyer', 'package_or_parcel', "
          "'media_mail_item', 'other_info_sheet', or 'other'."
      ),
  )
  is_template: bool = Field(
      False,
      description="True if this looks like an example / blank form, not a personal bill.",
  )

  # Rich detail
  amounts: List[AmountItem] = Field(
      default_factory=list,
      description="All amounts the model noticed, including examples or sample values.",
  )
  identity_requirements: List[IdentityRequirement] = Field(
      default_factory=list,
      description=(
          "Things the document says you need to identify yourself "
          "(account number, SSN, ticket number, policy number, etc.)."
      ),
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
  """
  System prompt for the deep Mail & Bills agent.

  NOTE: this is intentionally verbose so the model understands
  a wide range of mail types (bills, official letters, auto policies,
  contracts, HR letters, etc.) and multi-page OCR.
  """
  return (
      "You are an assistant that reads OCR text from mail delivered through the postal "
      "service for immigrants and their families. Documents may be in English or "
      "Spanish, and may be one page or many pages combined in a single OCR text.\n\n"
      "Your job is to:\n"
      "1) Understand what kind of document it is (bill, statement, policy, contract, letter, etc.).\n"
      "2) Extract key fields: amount_due, due_date, account_number, sender, service_address.\n"
      "3) List all amounts you see, with clear labels (even if they are just examples or fees).\n"
      "4) Describe what identity information is needed (account number, SSN, ticket or case number, "
      "   policy number, etc.).\n"
      "5) Describe how the person can pay or respond (online, bank, card, mail, phone, portal, etc.).\n"
      "6) Briefly flag how serious this looks (risk) and simple next steps.\n"
      "7) ALWAYS write a short summary in English (summary_en).\n"
      "8) ALSO write the same summary and a simple explanation in the TARGET LANGUAGE given by the user "
      "   (summary_translated and explanation_translated).\n\n"
      "LANGUAGE RULES:\n"
      "- summary_en MUST ALWAYS be in English, even if the original document is Spanish.\n"
      "- The user will provide a target_lang of 'es' or 'en'.\n"
      "- summary_translated and explanation_translated MUST be written in target_lang.\n"
      "- If target_lang == 'en', summary_en and summary_translated can be similar or identical.\n\n"
      "DOCUMENT TYPES & SPECIAL CASES:\n"
      "Valid document_type values include (choose the closest one):\n"
      "- 'utility_bill' (electricity, water, gas, internet, telephone, cable bills)\n"
      "- 'bank_statement' (checking, savings, trust, IRA statements)\n"
      "- 'credit_card_statement'\n"
      "- 'loan_statement' (mortgage, car loan, student loan, personal loan)\n"
      "- 'medical_bill'\n"
      "- 'tax_form' (W-2, 1099, 1040, etc.)\n"
      "- 'tax_notice' (audit letters, tax assessments)\n"
      "- 'insurance_policy' (general insurance policy documents)\n"
      "- 'auto_policy' (auto insurance policy documents)\n"
      "- 'investment_statement' (brokerage statements, trade confirmations, prospectus mail)\n"
      "- 'receipt' (receipt for purchases or deductible expenses)\n"
      "- 'court_notice' (court notices, summons, subpoenas, court orders)\n"
      "- 'legal_notice' (collection notices, default notices, privacy policy notifications)\n"
      "- 'contract' (general contracts, employment contracts, NDAs)\n"
      "- 'lease_agreement' / 'rental_agreement' (housing leases or rental contracts)\n"
      "- 'eviction_notice'\n"
      "- 'traffic_ticket'\n"
      "- 'government_letter' (general government correspondence not covered above)\n"
      "- 'benefit_letter' (Social Security, Medicare/Medicaid, benefit info)\n"
      "- 'voter_mail' (voter registration, election mail, absentee ballots)\n"
      "- 'license_id_mail' (driver's licenses, license plates, IDs)\n"
      "- 'census_or_survey' (census forms, official government surveys)\n"
      "- 'school_letter' (letters from schools)\n"
      "- 'work_letter' (letters from employers not already classified as contract or HR)\n"
      "- 'payroll_document' (pay stubs, W-2 copies mailed by employer)\n"
      "- 'hr_letter' (disciplinary notices, termination letters, HR benefit notifications)\n"
      "- 'personal_letter' (handwritten or personal correspondence)\n"
      "- 'greeting_card' (holiday, birthday, sympathy, congratulations cards)\n"
      "- 'magazine_or_newspaper'\n"
      "- 'catalog_or_flyer' (marketing mail, retail catalogs, promotional flyers)\n"
      "- 'package_or_parcel' (package slips or notices about deliveries/returns)\n"
      "- 'media_mail_item' (books, media, etc. when recognizable from the text)\n"
      "- 'other_info_sheet' (informational sheets, explanations, non-personal notices)\n"
      "- 'other' (if nothing fits).\n\n"
      "Many documents are MULTI-PAGE (for example auto policies, insurance policies, and contracts). "
      "The OCR text you receive may contain several pages glued together. ALWAYS treat the ENTIRE text "
      "as one combined document when summarizing and extracting fields.\n\n"
      "BLANK FORMS / TEMPLATES:\n"
      "- If the document is clearly a BLANK FORM or SAMPLE (example, template, dotted lines, "
      "  placeholder names, no real person), then:\n"
      "  * set is_template=true,\n"
      "  * set document_type like 'utility_bill', 'medical_bill', 'contract', etc. with a template meaning,\n"
      "  * leave fields.amount_due empty (or clearly example only),\n"
      "  * explain in the summaries that this looks like an example form, not a real personal bill.\n\n"
      "BILLS vs LETTERS vs CONTRACTS:\n"
      "- If there are many amounts, choose the main amount the person must pay now for fields.amount_due, "
      "  and put all amounts (examples, fees, totals) inside the 'amounts' list.\n"
      "- If the document is an INSURANCE POLICY, AUTO POLICY, or CONTRACT:\n"
      "  * use document_type 'insurance_policy', 'auto_policy', 'contract', or 'lease_agreement' / "
      "    'rental_agreement' as appropriate,\n"
      "  * in the summaries, focus on what the policy/contract covers, key obligations, important limits, "
      "    dates, cancellation rules, and non-payment consequences.\n"
      "- If the document is a LETTER with no clear bill or fine (doctor letter, school letter, work letter, "
      "  government letter, HR letter, or personal letter with no payment or case number):\n"
      "  * set document_type to 'school_letter', 'work_letter', 'government_letter', 'hr_letter', "
      "    'personal_letter', or 'other_info_sheet' as appropriate,\n"
      "  * leave fields like amount_due and due_date empty if there is nothing to pay,\n"
      "  * focus on explaining what the letter is about and any suggested next steps.\n\n"
      "You MUST respond with a single valid JSON object only, no extra text, exactly:\n"
      "{\n"
      '  \"detected_language\": \"en\" | \"es\" | \"other\",\n'
      '  \"document_type\": \"utility_bill\" | \"bank_statement\" | \"credit_card_statement\" | '
      '\"loan_statement\" | \"medical_bill\" | \"tax_form\" | \"tax_notice\" | '
      '\"insurance_policy\" | \"auto_policy\" | \"investment_statement\" | \"receipt\" | '
      '\"court_notice\" | \"legal_notice\" | \"contract\" | \"lease_agreement\" | '
      '\"rental_agreement\" | \"eviction_notice\" | \"traffic_ticket\" | \"government_letter\" | '
      '\"benefit_letter\" | \"voter_mail\" | \"license_id_mail\" | \"census_or_survey\" | '
      '\"school_letter\" | \"work_letter\" | \"payroll_document\" | \"hr_letter\" | '
      '\"personal_letter\" | \"greeting_card\" | \"magazine_or_newspaper\" | '
      '\"catalog_or_flyer\" | \"package_or_parcel\" | \"media_mail_item\" | '
      '\"other_info_sheet\" | \"other\",\n'
      '  \"is_template\": true | false,\n'
      '  \"summary_en\": \"...\",            // ALWAYS English\n'
      '  \"summary_translated\": \"...\",    // ALWAYS in target_lang\n'
      '  \"explanation_translated\": \"...\",// ALWAYS in target_lang\n'
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
      "If the document does not contain a certain piece of information, use empty strings and "
      "empty lists, and confidence 0.0. Do not invent URLs, ID numbers, policy numbers, or threats "
      "that are not present."
  )


def _build_user_prompt(payload: MailBillsRequest) -> str:
  hint_line = ""
  if payload.bill_hint:
    hint_line = f"Document hint: {payload.bill_hint}\n"

  return (
      f"Source language preference: {payload.source_lang}\n"
      f"Target language (for translated summary and explanation): {payload.target_lang}\n"
      f"{hint_line}"
      "Here is the OCR text from a bill, statement, policy, contract, letter, or other mail:\n"
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


def _parse_list(model_cls, key: str, parsed: dict) -> List[BaseModel]:
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
      # Skip bad entries rather than crashing.
      continue
  return out


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

  document_type = parsed.get("document_type") or "unknown"
  is_template = bool(parsed.get("is_template") or False)

  amounts = _parse_list(AmountItem, "amounts", parsed)
  identity_requirements = _parse_list(
      IdentityRequirement,
      "identity_requirements",
      parsed,
  )
  payment_methods = _parse_list(PaymentMethod, "payment_methods", parsed)
  risk_flags = _parse_list(RiskFlag, "risk_flags", parsed)
  followup_actions = _parse_list(FollowupAction, "followup_actions", parsed)

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
  calls OpenAI, and returns structured bill/letter/policy/contract info.
  """
  try:
    parsed = await _call_openai_for_mailbills(req)
    return _build_response_from_llm(req, parsed)
  except Exception as exc:  # noqa: BLE001
    raise HTTPException(
        status_code=500,
        detail={"ok": False, "message": str(exc)},
    ) from exc
