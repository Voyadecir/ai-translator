"""MailBills Agent with JSON interpret endpoint.

This module implements FastAPI routes for the Mail & Bills Helper.  It accepts OCR text
and returns structured extraction + summary + plain-language explanation in English,
plus a mirrored Spanish translation of those outputs (NO second reasoning pass).

Key guarantees:
- Never stop early (extract ALL list items).
- English output first.
- Spanish output is a translation of English output.
- OCR pipeline is NOT modified here.
- If the LLM step fails, the endpoint falls back to basic summary so uploads still work.

The endpoint supports JSON requests with `text`, `target_lang`, `ui_lang` and an optional `source_lang`.  It returns:
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

# Import the existing mailbills_agent core (translation + OCR processing)
from ai_translator import mailbills_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mailbills"])


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
        translation_result = mailbills_agent.translate_text(
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

        # 4) NEW: Robust extraction + summary + plain-language explanation (English first)
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
                "- This looks like a document upload.\\n"
                "- Extraction is temporarily unavailable; showing a basic summary.\\n"
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

        # 6) Lightweight regex-based items (kept, but no longer the main product)
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

    Expects an uploaded PDF or image file. Returns the same output structure as
    the original implementation.
    """
    try:
        file_bytes = await file.read()
        result = mailbills_agent.process_document(
            file_bytes, source_lang=source_lang, target_lang=target_lang, user_preferences=None
        )
        return JSONResponse(status_code=200, content={"ok": True, **result})
    except Exception as exc:
        logger.exception(f"mailbills interpret-file failed: {exc}")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


# ------------------------------
# Helpers
# ------------------------------

def _normalize_ocr_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _guess_source_lang(text: str) -> str:
    # Best-effort: if a lot of Spanish markers appear, guess 'es'
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

    ui_translator = getattr(mailbills_agent, "ui_translator", None)
    for word in ambiguous_words[:10]:
        prompts.append(
            {
                "word": word,
                "prompt": ui_translator.get_clarification_prompt(word, ui_lang) if hasattr(ui_translator, "get_clarification_prompt") else None,
                "question": f"Can you clarify what '{word}' refers to?",
            }
        )

    return prompts


# -------------------------------------------------------------------------
# NEW: Robust doc extraction + summary + explanation
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
    """Call OpenAI and parse a JSON object back.

    NOTE: We intentionally avoid `response_format=...` here to remain compatible with older
    OpenAI SDK versions that don't support it.
    """
    client = getattr(mailbills_agent, "openai_client", None)
    if client is None:
        raise _LLMError("OpenAI client not initialized (missing OPENAI_API_KEY)")

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
    """Return English-first structured extraction + summary + plain-language explanation.

    IMPORTANT:
    - Must not stop early.
    - Must extract *all* list items if a numbered list exists.
    - Must work for recipes, receipts, forms, diagrams, plans, posters, etc.
    """
    text = (ocr_text or "").strip()
    if not text:
        return {
            "document_type": "unknown",
            "english_summary": "",
            "english_explanation": "",
            "extracted": {
                "document_type_guess": "unknown",
                "key_facts": {},
                "items": [],
                "recommended_actions": [],
            },
            "warnings": ["Empty OCR text"],
        }

    # Guard against huge inputs: preserve full meaning but reduce token bloat
    text_for_llm = text
    trunc_warning = None
    if len(text_for_llm) > 20000:
        trunc_warning = "OCR text was very long; it was truncated for analysis."
        text_for_llm = text_for_llm[:20000]

    system = (
        "You are Voyadecir, a document-understanding assistant. "
        "Your job is to extract ALL relevant information and explain it in plain English. "
        "Never stop early. Never output a single example when multiple items exist."
    )

    instruction = (
        "TASK:\n"
        "1) Identify the document type (best guess).\n"
        "2) Extract key facts and ALL list/table items. If the text contains a numbered list, "
        "return every item you can find (e.g., 1..10).\n"
        "3) Provide an English summary (2-6 bullets).\n"
        "4) Provide an English explanation (plain-language, calm, 6-12 bullets) describing what it is, "
        "what matters, and what to do next.\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY valid JSON with this shape:\n"
        "{\n"
        '  "document_type": string,\n'
        '  "english_summary": [string, ...],\n'
        '  "english_explanation": [string, ...],\n'
        '  "extracted": {\n'
        '     "key_facts": { "dates":[], "amounts":[], "deadlines":[], "names":[], "addresses":[], "phones":[], "urls":[], "ids":[] },\n'
        '     "items": [ { "n": 1, "title": "...", "detail": "..." }, ... ],\n'
        '     "recommended_actions": [string, ...]\n'
        "  },\n"
        '  "warnings": [string, ...]\n'
        "}\n\n"
        "Rules:\n"
        "- If you are unsure, set fields to empty lists/objects, do not invent.\n"
        "- If there is a numbered list, include ALL items.\n"
        "- Keep items in the original order.\n"
        "- No markdown, no extra text outside JSON.\n"
    )

    enrichment_hint: Dict[str, Any] = {}
    try:
        if isinstance(enrichment, dict):
            # Keep it small; we only need the highlights.
            for k in [
                "ambiguous_words",
                "idioms",
                "slang",
                "religious_terms",
                "road_signs",
                "dictionary_data",
                "profanity",
                "tone",
            ]:
                if k in enrichment:
                    enrichment_hint[k] = enrichment.get(k)
    except Exception:
        enrichment_hint = {}

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                instruction
                + "\nENRICHMENT_HINTS (from internal utils):\n"
                + json.dumps(enrichment_hint, ensure_ascii=False)[:4000]
                + "\n\nOCR_TEXT:\n"
                + text_for_llm
            ),
        },
    ]

    data = _call_openai_json(messages)

    # Normalize into the exact shape we want to return.
    english_summary_list = data.get("english_summary") or []
    english_explanation_list = data.get("english_explanation") or []
    extracted = data.get("extracted") or {}
    warnings = data.get("warnings") or []
    if trunc_warning:
        warnings = (warnings or []) + [trunc_warning]

    # Convert list bullets into a single string for the UI boxes.
    english_summary = _bullets_to_text(english_summary_list)
    english_explanation = _bullets_to_text(english_explanation_list)

    return {
        "document_type": data.get("document_type") or "unknown",
        "english_summary": english_summary,
        "english_explanation": english_explanation,
        "extracted": extracted,
        "warnings": warnings,
    }


def _bullets_to_text(items: List[str]) -> str:
    if not items:
        return ""
    lines = []
    for s in items:
        s = (s or "").strip()
        if not s:
            continue
        # Ensure bullets
        if not s.startswith("-"):
            s = "- " + s
        lines.append(s)
    return "\n".join(lines).strip()


def _mirror_to_spanish(english_summary: str, english_explanation: str, doc_type: str) -> Tuple[str, str]:
    """Mirror Spanish output as a translation of the English output.

    IMPORTANT: This is translation only, not re-analysis.
    """
    combined = (
        "ENGLISH SUMMARY:\n"
        + (english_summary or "").strip()
        + "\n\nENGLISH EXPLANATION:\n"
        + (english_explanation or "").strip()
    ).strip()

    if not combined:
        return "", ""

    t = mailbills_agent.translate_text(
        combined,
        source_lang="en",
        target_lang="es",
        document_type=doc_type or "ocr_text",
        user_preferences=None,
    )

    spanish = (t.get("translated_text") or "").strip()
    if not spanish:
        return "", ""

    # Split back out, best-effort.
    parts = spanish.split("ENGLISH EXPLANATION:")
    if len(parts) == 2:
        sp_sum = parts[0].replace("ENGLISH SUMMARY:", "").strip()
        sp_exp = parts[1].strip()
        return sp_sum, sp_exp

    # Fallback if split fails
    return spanish, ""


# -------------------------------------------------------------------------
# Legacy extraction helpers (kept for compatibility)
# -------------------------------------------------------------------------

def _summarize_translation(translated_text: str, lang: str) -> str:
    """
    Very lightweight fallback summary: first 1-2 sentences.
    Used ONLY when the robust extraction step fails.
    """
    t = (translated_text or "").strip()
    if not t:
        return ""

    # Split on sentence boundaries (rough).
    parts = re.split(r"(?<=[\.\!\?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return t[:200].strip()

    return " ".join(parts[:2]).strip()


def _extract_identity_items(text: str) -> List[str]:
    """
    Extract things that look like identifying info from OCR text (very lightweight).
    """
    if not text:
        return []

    patterns = [
        r"\baccount\b",
        r"\bacct\b",
        r"\bmember\b",
        r"\bpolicy\b",
        r"\bssn\b",
        r"\bid\b",
        r"\bcase\b",
        r"\bref(erence)?\b",
    ]
    found = []
    lower = text.lower()
    for pat in patterns:
        if re.search(pat, lower):
            found.append(pat.strip("\\b"))
    return sorted(set(found))


def _extract_payment_items(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract payment instructions and other amounts (very lightweight).
    """
    if not text:
        return [], []

    payment_items: List[str] = []
    other_amounts: List[str] = []

    lower = text.lower()

    if "amount due" in lower or "balance due" in lower:
        payment_items.append("Amount due / Balance due")

    if "due date" in lower or "pay by" in lower:
        payment_items.append("Due date / Pay-by date")

    # Extract dollar amounts
    amounts = re.findall(r"\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})", text)
    amounts = [a.strip() for a in amounts if a.strip()]
    if amounts:
        other_amounts.extend(amounts[:25])

    return payment_items, other_amounts
