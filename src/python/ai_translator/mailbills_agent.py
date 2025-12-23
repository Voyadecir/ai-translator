"""MailBills Agent with JSON interpret endpoint.

This module defines the MailBillsAgent class and associated FastAPI routes.  It has been
modified to support JSON input for interpretation, and exposes a separate file-based
endpoint for legacy uploads.

The default `/api/mailbills/interpret` endpoint now expects a JSON body with
`text`, `target_lang`, `ui_lang` and an optional `source_lang`.  It returns a JSON
response containing a `summary`, lists of `identity_items`, `payment_items`,
and `other_amounts_items`, along with the translated text and cultural
enrichment.  The original file-upload interpretation has been moved to
`/api/mailbills/interpret-file`.

"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
import os

from openai import OpenAI

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .utils.ocr_preprocessor import assess_image, preprocess_for_ocr
from .utils.ocr_postprocessor import clean_ocr_output
from .utils.translation_engine import translate_text
from .utils.language_detector import detect_language
from .utils.translation_dictionaries import AUTHORITATIVE_SOURCES
from .utils.ui_translation import ui_translator

logger = logging.getLogger(__name__)


class InterpretRequest(BaseModel):
    """JSON schema for interpreting OCR output.

    Attributes
    ----------
    text : str
        The raw OCR text extracted from a document.
    target_lang : str, default="es"
        The language to translate the document into.
    ui_lang : str, default="en"
        The caller's UI language (not currently used by the model but reserved for future
        enhancements).
    source_lang : str, default="en"
        The language of the original document.  If omitted, a best guess is used.
    """

    text: str = Field(..., description="The document text to interpret and translate")
    target_lang: str = Field("es", description="Target language code")
    ui_lang: str = Field("en", description="UI language code")
    source_lang: str = Field("auto", description="Source language code")


class MailBillsAgent:
    """
    Main deep agent for omniscient document translation
    (Docstring unchanged from original for brevity)
    """

    def __init__(self):
        """Initialize agent with Azure clients and utilities"""
        di_endpoint = (
            os.getenv("AZURE_DOCINTEL_ENDPOINT")
            or os.getenv("AZURE_DI_ENDPOINT")
            or os.getenv("AZURE_DOC_INTEL_ENDPOINT")
        )
        di_key = (
            os.getenv("AZURE_DOCINTEL_KEY")
            or os.getenv("AZURE_DI_API_KEY")
            or os.getenv("AZURE_DOC_INTEL_KEY")
        )

        if di_endpoint and di_key:
            try:
                self.doc_intel_client = DocumentIntelligenceClient(
                    endpoint=di_endpoint, credential=AzureKeyCredential(di_key)
                )
                logger.info("Azure Document Intelligence initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Document Intelligence: {e}")
                self.doc_intel_client = None
        else:
            self.doc_intel_client = None
            logger.warning("Azure Document Intelligence credentials not set")

        # OpenAI client (standard OpenAI, not Azure)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not set")

        self.document_types = self._load_document_types()
        self.default_source_lang = "en"
        self.default_target_lang = "es"

    def _load_document_types(self) -> Dict[str, Dict]:
        """
        Load all supported document types (abbreviated).
        """
        return {
            # Example subset of document types for demonstration.
            "electric_bill": {
                "name": "Electric Bill",
                "category": "utility",
                "keywords": [
                    "electric",
                    "electricity",
                    "kWh",
                    "meter reading",
                    "billing period",
                ],
                "authority": "Utility",
            },
            "water_bill": {
                "name": "Water Bill",
                "category": "utility",
                "keywords": ["water", "sewer", "gallons", "water service"],
                "authority": "Utility",
            },
        }

    def process_document(
        self,
        image_bytes: bytes,
        source_lang: str = "en",
        target_lang: str = "es",
        user_preferences: Optional[Dict] = None,
    ) -> Dict:
        """
        Main processing pipeline - orchestrates OCR → translation.

        This implementation mirrors the original for completeness.
        """
        result = {
            "document_type": None,
            "ocr_text": "",
            "translated_text": "",
            "confidence_score": 0.0,
            "warnings": [],
            "cultural_notes": [],
            "clarifications_needed": [],
            "enrichment": {},
            "pdf_url": None,
            "metadata": {"processing_steps": [], "timestamp": datetime.now().isoformat()},
        }

        try:
            logger.info("Step 1: Assessing image quality...")
            quality = assess_image(image_bytes)
            result["metadata"]["image_quality"] = quality
            result["metadata"]["processing_steps"].append("image_quality_assessment")

            if quality.get("needs_preprocessing", False):
                logger.info("Step 2: Preprocessing image for better OCR...")
                aggressive = quality.get("recommended_aggressive", False)
                enhanced_bytes, preprocess_metadata = preprocess_for_ocr(
                    image_bytes, aggressive
                )
                result["metadata"]["preprocessing"] = preprocess_metadata
                result["metadata"]["processing_steps"].append("image_preprocessing")
                image_to_ocr = enhanced_bytes
            else:
                logger.info("Step 2: Image quality good, skipping preprocessing")
                image_to_ocr = image_bytes

            logger.info("Step 3: Running Azure Document Intelligence OCR...")
            ocr_raw = self._run_azure_ocr(image_to_ocr)
            result["metadata"]["processing_steps"].append("azure_ocr")

            if not ocr_raw:
                result["warnings"].append("OCR failed to extract text")
                return result

            logger.info("Step 4: Detecting document type...")
            doc_type = self._detect_document_type(ocr_raw)
            result["document_type"] = doc_type
            result["metadata"]["processing_steps"].append("document_type_detection")

            logger.info("Step 5: Postprocessing OCR output...")
            ocr_cleaned = clean_ocr_output(ocr_raw, doc_type)
            result["ocr_text"] = ocr_cleaned["cleaned_text"]
            result["metadata"]["ocr_postprocessing"] = ocr_cleaned
            result["metadata"]["processing_steps"].append("ocr_postprocessing")

            logger.info("Step 6: Translating with cultural intelligence...")
            translation_result = translate_text(
                text=result["ocr_text"],
                source_lang=source_lang,
                target_lang=target_lang,
                document_type=doc_type,
                user_preferences=user_preferences,
            )

            result["translated_text"] = translation_result["translated_text"]
            result["confidence_score"] = translation_result["confidence_score"]
            result["warnings"].extend(translation_result["warnings"])
            result["cultural_notes"].extend(translation_result["cultural_notes"])
            result["enrichment"] = translation_result["enrichment"]
            result["metadata"]["processing_steps"].append("translation_engine")

            logger.info("Step 7: Checking for ambiguous words...")
            ambiguous = translation_result["enrichment"].get("ambiguous_words", [])
            if ambiguous:
                result["clarifications_needed"] = self._prepare_clarifications(
                    ambiguous, target_lang
                )
                result["metadata"]["processing_steps"].append("clarification_detection")

            logger.info("Step 8: Generating PDF placeholder...")
            result["metadata"]["processing_steps"].append("pdf_generation")

            logger.info(
                f"Document processing complete. Type: {doc_type}, Confidence: {result['confidence_score']:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Document processing error: {e}")
            result["warnings"].append(f"Processing error: {str(e)}")
            return result

    def _run_azure_ocr(self, image_bytes: bytes) -> Optional[str]:
        """Run Azure Document Intelligence OCR"""
        if not self.doc_intel_client:
            logger.error("Azure Document Intelligence client not initialized")
            return None

        try:
            poller = self.doc_intel_client.begin_analyze_document(
                "prebuilt-read", image_bytes
            )
            result = poller.result()
            text_content = []
            for page in result.pages:
                for line in page.lines:
                    text_content.append(line.content)
            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"Azure OCR error: {e}")
            return None

    def _detect_document_type(self, ocr_text: str) -> Optional[str]:
        """Detect document type from OCR text via keyword matching"""
        for doc_type, metadata in self.document_types.items():
            keywords = metadata.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in ocr_text.lower():
                    logger.info(f"Document type detected by keywords: {doc_type}")
                    return doc_type
        return "unknown"

    def _prepare_clarifications(
        self, ambiguous_words: List[Dict], target_lang: str
    ) -> List[Dict]:
        """Prepare clarification questions for ambiguous words"""
        clarifications = []
        for word_info in ambiguous_words:
            word = word_info["word"]
            meanings = word_info.get("meanings", [])
            question_text = ui_translator.translate_ui_element(
                f"Which meaning of '{word}' is correct?",
                element_type="label",
                target_lang=target_lang,
            )
            clarifications.append(
                {
                    "word": word,
                    "question": question_text,
                    "options": meanings,
                    "type": "multiple_choice",
                }
            )
        return clarifications

    def get_authoritative_sources(self) -> List[Dict]:
        """Return list of authoritative dictionary sources"""
        sources = []
        for source_key, source_data in AUTHORITATIVE_SOURCES.items():
            sources.append(
                {
                    "name": source_data["name"],
                    "url": source_data["url"],
                    "category": source_data.get("category", "general"),
                    "description": source_data.get("description", ""),
                }
            )
        return sources


# Global agent instance
mailbills_agent = MailBillsAgent()

# FastAPI router for mail-bills endpoints
router = APIRouter()


@router.get("/mailbills/interpret")
async def mailbills_interpret_alive() -> JSONResponse:
    """Health check endpoint for the interpret route."""
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
      - summary: a concise explanation of the document
      - identity_items: list of items needed for identification (empty if none)
      - payment_items: list of payment instructions (empty if none)
      - other_amounts_items: list of other important amounts (empty if none)
      - translated_text: the full translated text
      - confidence_score: translation confidence
      - warnings: list of warnings
      - cultural_notes: list of cultural notes
      - enrichment: extra information from the translation engine
    """
    try:
        detected_source, detection_confidence = detect_language(req.text, fallback="en")
        source_lang = req.source_lang if req.source_lang != "auto" else detected_source

        translation_result = translate_text(
            text=req.text,
            source_lang=source_lang or "en",
            target_lang=req.target_lang or "es",
            document_type="ocr_text",
            user_preferences=None,
        )

        translated = translation_result.get("translated_text", "")
        summary = _summarize_translation(translated, req.target_lang)

        enrichment = translation_result.get("enrichment", {}) or {}
        ambiguous_words = enrichment.get("ambiguous_words", [])
        clarifications = _build_clarifications(ambiguous_words, req.ui_lang or req.target_lang)

        identity_items = _extract_identity_items(req.text)
        payment_items, other_amounts = _extract_payment_items(req.text)

        response = {
            "ok": True,
            "summary": summary,
            "identity_items": identity_items,
            "payment_items": payment_items,
            "other_amounts_items": other_amounts,
            "translated_text": translated,
            "confidence_score": translation_result.get("confidence_score", 0.0),
            "warnings": translation_result.get("warnings", []),
            "cultural_notes": translation_result.get("cultural_notes", []),
            "enrichment": enrichment,
            "clarifications": clarifications,
            "detected_source_lang": source_lang,
            "detection_confidence": detection_confidence,
        }
        return JSONResponse(status_code=200, content=response)
    except Exception as exc:
        logger.exception(f"JSON interpret failed: {exc}")
        return JSONResponse(
            status_code=500, content={"ok": False, "error": str(exc)}
        )


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

    Expects an uploaded PDF or image file.  Returns the same output structure as
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
        return JSONResponse(
            status_code=500, content={"ok": False, "error": str(exc)}
        )
# ------------------------------
# Helpers
# ------------------------------


def _summarize_translation(translated: str, target_lang: str) -> str:
    clean = (translated or "").replace("\n", " ").strip()
    if not clean:
        return ""

    sentences = re.split(r"(?<=[\.\!\?])\s+", clean)
    summary = " ".join(sentences[:2]).strip()
    return summary or clean[:240]


def _extract_identity_items(text: str) -> List[str]:
    patterns = [
        r"account\s*(?:number|no\.?|#)\s*[:#]?\s*([A-Za-z0-9\-]+)",
        r"customer\s*id\s*[:#]?\s*([A-Za-z0-9\-]+)",
        r"invoice\s*[:#]?\s*([A-Za-z0-9\-]+)",
        r"policy\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Za-z0-9\-]+)",
    ]

    found: List[str] = []
    lower_text = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lower_text, flags=re.IGNORECASE):
            val = match.group(1)
            if val and val not in found:
                found.append(val)

    # Also pick lines with obvious identifiers
    for line in text.splitlines():
        if any(keyword in line.lower() for keyword in ["account", "customer", "invoice", "policy"]):
            cleaned = line.strip()
            if cleaned and cleaned not in found:
                found.append(cleaned)

    return found[:5]


def _extract_payment_items(text: str) -> (List[str], List[str]):
    amounts = []
    other_amounts: List[str] = []
    due_dates: List[str] = []
    currency_pattern = re.compile(r"(?:USD|US\$|\$|€|£)\s?\d[\d,]*(?:\.\d{2})?")
    date_pattern = re.compile(r"(?:due|fecha|vence)[^\d]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})", re.IGNORECASE)

    for line in text.splitlines():
        amount_matches = currency_pattern.findall(line)
        if amount_matches:
            if any(word in line.lower() for word in ["due", "pagar", "amount due", "total", "balance"]):
                amounts.extend(amount_matches)
            else:
                other_amounts.extend(amount_matches)

        date_matches = date_pattern.findall(line)
        due_dates.extend(date_matches)

    payment_items: List[str] = []
    if amounts:
        payment_items.append("Amount due: " + ", ".join(dict.fromkeys(amounts)))
    if due_dates:
        payment_items.append("Due date(s): " + ", ".join(dict.fromkeys(due_dates)))

    return payment_items[:5], other_amounts[:5]


def _build_clarifications(ambiguous_words: List[str], lang: str) -> List[str]:
    if not ambiguous_words:
        return []

    prompts = []
    for word in ambiguous_words:
        prompts.append(
            {
                "word": word,
                "prompt": ui_translator.get_clarification_prompt(word, lang) if hasattr(ui_translator, "get_clarification_prompt") else None,
                "question": f"Can you clarify what '{word}' refers to?",
            }
        )

    return prompts

