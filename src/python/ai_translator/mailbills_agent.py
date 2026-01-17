"""MailBills Agent with JSON interpret endpoint.

This module implements FastAPI routes for the Mail & Bills Helper. It accepts OCR text
and returns structured extraction + summary + plain-language explanation in English,
plus a mirrored Spanish translation of those outputs (NO second reasoning pass).

Key guarantees:
- Never stop early (extract ALL list items).
- English output first.
- Spanish output is a translation of English output.
- OCR pipeline is NOT modified here.
- If the LLM step fails, the endpoint falls back to basic summary so uploads still work.

The endpoint supports JSON requests with `text`, `target_lang`, `ui_lang` and an optional `source_lang`. It returns:
- `english_summary`, `english_explanation`
- `spanish_summary`, `spanish_explanation`
- `extracted` (document_type, items, key_facts, recommended_actions)
- Legacy fields for compatibility: `summary`, lists of `identity_items`, `payment_items`,
and `other_amounts_items`, and `translated_text`.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# IMPORTANT:
# This file defines the FastAPI router for the Mail & Bills Helper.
# It MUST NOT import `ai_translator.mailbills_agent` (itself), or Python will
# resolve the import to this module and you'll get runtime errors like:
#   "module 'ai_translator.mailbills_agent' has no attribute 'translate_text'"
#
# Use the shared translation engine instead.
from ai_translator.utils.translation_engine import translate_text as _translate_text
from ai_translator.utils.translation_engine import translation_engine as _translation_engine

logger = logging.getLogger(__name__)
router = APIRouter()


# -------------------------------------------------------------------------
# Request / Response Models
# -------------------------------------------------------------------------

class InterpretRequest(BaseModel):
    text: str
    target_lang: Optional[str] = "es"
    ui_lang: Optional[str] = "en"
    source_lang: Optional[str] = None


# -------------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------------

@router.get("/mailbills/interpret")
async def mailbills_interpret_alive() -> JSONResponse:
    """Health check for the JSON interpreter."""
    return JSONResponse(
        status_code=200, content={"ok": True, "message": "mailbills/interpret alive"}
    )


@router.post("/mailbills/interpret")
async def mailbills_interpret_json(req: InterpretRequest) -> JSONResponse:
    """
    Interpret and translate OCR text from the Mail & Bills page.

    This endpoint accepts a JSON body with keys:
      - text: the raw OCR output as a string
      - target_lang: target language code (e.g. 'es' or 'en')
      - ui_lang: UI language code (for future use)
      - source_lang: optional source language code; defaults to English

    It returns a JSON object with:
      - summary: a concise explanation of the document (legacy)
      - english_summary / english_explanation
      - spanish_summary / spanish_explanation (mirrored translation of English)
      - extracted: structured extraction payload
      - identity_items / payment_items / other_amounts_items (legacy)
      - translated_text: the full translated text (legacy)
    """
    try:
        raw_text = (req.text or "").strip()
        if not raw_text:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Missing OCR text (text is empty)."},
            )

        # 1) Normalize OCR text (light)
        clean_text = _normalize_ocr_text(raw_text)

        # 2) Detect source language if not provided (best effort)
        source_lang = (req.source_lang or "").strip() or _guess_source_lang(clean_text)
        detection_confidence = 0.6  # placeholder; keep for compatibility

        # 3) Translate using existing pipeline (this is where your utils matter)
        translation_result = _translate_text(
            clean_text,
            source_lang=source_lang or "en",
            target_lang=req.target_lang or "es",
            document_type="ocr_text",
            user_preferences=None,
        )
        translated_full = translation_result.get("translated_text", "")
        enrichment = translation_result.get("enrichment", {}) or {}
        ambiguous_words = enrichment.get("ambiguous_words", [])
        clarifications = _build_clarifications(ambiguous_words, req.ui_lang or req.target_lang)

        # 4) Robust extraction + summary + plain-language explanation (English first)
        agent_warnings: List[str] = []
        try:
            analysis = _analyze_document_english(
                ocr_text=clean_text,
                ui_lang=req.ui_lang or "en",
                source_lang=source_lang or "en",
                enrichment=enrichment,
            )

            english_summary = analysis.get("english_summary", "")
            english_explanation = analysis.get("english_explanation", "")
            extracted = analysis.get("extracted", {})
            doc_type_guess = analysis.get("document_type", "unknown")
            agent_warnings = analysis.get("warnings", []) or []
        except Exception as e:
            # IMPORTANT: Do not break uploads just because the LLM step failed.
            logger.exception(f"LLM extraction failed; falling back. Error: {e}")
            agent_warnings = [f"LLM extraction failed; using fallback summary. Error: {e}"]
            doc_type_guess = "unknown"
            extracted = {"key_facts": {}, "items": [], "recommended_actions": [], "notes": []}

            # Fallback: keep the app usable. Basic summary from the translated text.
            english_summary = _summarize_translation(translated_full, "en")
            english_explanation = (
                "- This looks like a document upload.\n"
                "- Extraction is temporarily unavailable; showing a basic summary.\n"
                "- If this keeps happening, check service configuration (OPENAI_API_KEY) and logs."
            )

        # 5) Mirror Spanish as a translation of the English outputs (NO re-analysis)
        try:
            spanish_summary, spanish_explanation = _mirror_to_spanish(
                english_summary=english_summary,
                english_explanation=english_explanation,
                doc_type=doc_type_guess,
            )
        except Exception as e:
            logger.exception(f"Spanish mirror failed; continuing without it. Error: {e}")
            agent_warnings = (agent_warnings or []) + [f"Spanish mirror failed: {e}"]
            spanish_summary, spanish_explanation = "", ""

        # 6) Lightweight regex-based items (kept for compatibility)
        identity_items = _extract_identity_items(clean_text)
        payment_items, other_amounts = _extract_payment_items(clean_text)

        response = {
            "ok": True,

            # Backwards compatible field (many clients use this)
            "summary": english_summary,

            # New robust fields
            "english_summary": english_summary,
            "english_explanation": english_explanation,
            "spanish_summary": spanish_summary,
            "spanish_explanation": spanish_explanation,

            # Structured extraction payload
            "document_type": doc_type_guess,
            "extracted": extracted,

            # Legacy fields
            "identity_items": identity_items,
            "payment_items": payment_items,
            "other_amounts_items": other_amounts,
            "translated_text": translated_full,

            # Compatibility fields you already returned
            "confidence_score": translation_result.get("confidence_score", None),
            "enrichment": enrichment,
            "clarifications": clarifications,
            "detected_source_lang": source_lang,
            "detection_confidence": detection_confidence,

            # Warnings
            "warnings": agent_warnings,
        }
        return JSONResponse(status_code=200, content=response)

    except Exception as exc:
        logger.exception(f"JSON interpret failed: {exc}")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


@router.get("/mailbills/interpret-file")
async def mailbills_interpret_file_alive() -> JSONResponse:
    """Health check for the file-upload interpreter."""
    return JSONResponse(
        status_code=200, content={"ok": True, "message": "mailbills/interpret-file alive"}
    )


@router.post("/mailbills/interpret-file")
async def mailbills_interpret_file(
    file: UploadFile = File(...),
    source_lang: str = Query("en", description="Source language code"),
    target_lang: str = Query("es", description="Target language code"),
) -> JSONResponse:
    """
    Legacy endpoint for interpreting and translating uploaded files.

    NOTE: In the current Voyadecir architecture, OCR happens in Azure Functions and
    this service receives OCR text via /mailbills/interpret.
    """
    return JSONResponse(
        status_code=410,
        content={
            "ok": False,
            "error": "Deprecated endpoint. Use POST /mailbills/interpret with OCR text.",
        },
    )


# ------------------------------
# Helpers
# ------------------------------

def _normalize_ocr_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _guess_source_lang(text: str) -> str:
    sample = (text or "").lower()
    spanish_hits = sum(
        1 for w in [" el ", " la ", " de ", " y ", " que ", " por ", " para ", " una ", " un "]
        if w in f" {sample} "
    )
    return "es" if spanish_hits >= 3 else "en"


def _build_clarifications(ambiguous_words: List[str], ui_lang: Optional[str]) -> List[Dict[str, Any]]:
    prompts = []
    if not ambiguous_words:
        return prompts
    for word in ambiguous_words[:10]:
        prompts.append(
            {
                "word": word,
                "prompt": None,
                "question": f"Can you clarify what '{word}' refers to?",
            }
        )
    return prompts


# -------------------------------------------------------------------------
# Robust doc extraction + summary + explanation
# -------------------------------------------------------------------------

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class _LLMError(RuntimeError):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(_LLMError),
)
def _call_openai_json(messages: List[Dict[str, str]], max_tokens: int = 1400) -> Dict[str, Any]:
    """Call OpenAI and parse a JSON object back."""
    client = getattr(_translation_engine, "client", None)
    if client is None:
        raise _LLMError("OpenAI client not initialized (check OPENAI_API_KEY / Azure OpenAI settings)")

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=max_tokens,
        )
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise _LLMError("Empty model response")
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise _LLMError(f"Model returned non-JSON: {e}")
    except Exception as e:
        raise _LLMError(str(e))


def _analyze_document_english(
    ocr_text: str,
    ui_lang: str,
    source_lang: str,
    enrichment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    text = (ocr_text or "").strip()
    if not text:
        return {
            "document_type": "unknown",
            "english_summary": "",
            "english_explanation": "",
            "extracted": {"document_type_guess": "unknown", "key_facts": {}, "items": [], "recommended_actions": [], "notes": []},
            "warnings": [],
        }

    prompt = (
        "You are a document-understanding assistant.\n"
        "Return ONLY valid JSON.\n"
        "Task:\n"
        "1) Identify document_type.\n"
        "2) Extract key_facts and items (do not stop early).\n"
        "3) Write english_summary and english_explanation in plain language.\n"
        "Output JSON keys: document_type, english_summary, english_explanation, extracted, warnings.\n"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text[:12000]},
    ]

    obj = _call_openai_json(messages)

    # Minimal normalization
    doc_type = str(obj.get("document_type") or "unknown")
    english_summary = str(obj.get("english_summary") or "").strip()
    english_explanation = str(obj.get("english_explanation") or "").strip()
    extracted = obj.get("extracted") or {}
    warnings = obj.get("warnings") or []

    if not isinstance(extracted, dict):
        extracted = {}

    return {
        "document_type": doc_type,
        "english_summary": english_summary,
        "english_explanation": english_explanation,
        "extracted": extracted,
        "warnings": warnings if isinstance(warnings, list) else [],
    }


# -------------------------------------------------------------------------
# Legacy extraction helpers (kept for compatibility)
# -------------------------------------------------------------------------

def _extract_identity_items(text: str) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    hits = []
    for pat in [
        r"\bAccount\s*#?:\s*([A-Za-z0-9\-\*]{4,})",
        r"\bPolicy\s*#?:\s*([A-Za-z0-9\-\*]{4,})",
        r"\bMember\s*ID\s*#?:\s*([A-Za-z0-9\-\*]{4,})",
    ]:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            hits.append(m.group(0).strip())
    return hits


def _extract_payment_items(text: str) -> Tuple[List[str], List[str]]:
    t = (text or "").strip()
    if not t:
        return [], []
    payments = []
    others = []
    for pat in [
        r"\bTotal\s+Due\b.*",
        r"\bAmount\s+Due\b.*",
        r"\bBalance\b.*",
    ]:
        for m in re.finditer(pat, t, flags=re.IGNORECASE):
            line = m.group(0).strip()
            if line:
                payments.append(line)
    return payments[:20], others[:20]


def _summarize_translation(translated_text: str, lang: str) -> str:
    t = (translated_text or "").strip()
    if not t:
        return ""
    parts = re.split(r"(?<=[\.\!\?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return t[:200].strip()
    return " ".join(parts[:2]).strip()


def _mirror_to_spanish(english_summary: str, english_explanation: str, doc_type: str) -> Tuple[str, str]:
    combined = (
        "ENGLISH SUMMARY:\n"
        + (english_summary or "").strip()
        + "\n\nENGLISH EXPLANATION:\n"
        + (english_explanation or "").strip()
    ).strip()

    if not combined:
        return "", ""

    t = _translate_text(
        combined,
        source_lang="en",
        target_lang="es",
        document_type=doc_type or "ocr_text",
        user_preferences=None,
    )

    spanish = (t.get("translated_text") or "").strip()
    if not spanish:
        return "", ""

    parts = spanish.split("ENGLISH EXPLANATION:")
    if len(parts) == 2:
        sp_sum = parts[0].replace("ENGLISH SUMMARY:", "").strip()
        sp_exp = parts[1].strip()
        return sp_sum, sp_exp

    return spanish, ""
