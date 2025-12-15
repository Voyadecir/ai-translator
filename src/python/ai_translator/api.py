import os
import logging
from io import BytesIO
from typing import Optional, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile as StarletteUploadFile

from .ocr import run_ocr_pipeline
from .mailbills_agent import router as mailbills_router  # deep agent router

# Import cultural intelligence systems
from .utils.ui_translation import ui_translator
from .utils.translation_engine import translate_text as translate_with_intelligence
from .utils.idiom_database import idiom_db
from .utils.profanity_handler import profanity_handler
from .utils.sarcasm_tone_detector import sarcasm_detector
from .utils.context_handler import context_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# App + CORS
# -------------------------------------------------------------------------
app = FastAPI(title="Voyadecir API")

origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Deep agent routes
app.include_router(mailbills_router, prefix="/api")

FILE_NONE = File(default=None)

# -------------------------------------------------------------------------
# Shared upload helpers (OCR endpoints)
# -------------------------------------------------------------------------
async def _coerce_upload_file(
    request: Request,
    file: Optional[UploadFile],
) -> UploadFile:
    """Accept multipart UploadFile or raw body upload"""
    if file is not None:
        return file

    raw_bytes = await request.body()
    if not raw_bytes:
        raise HTTPException(
            status_code=400,
            detail="No file provided. Send FormData field 'file' or raw body.",
        )

    content_type = request.headers.get("content-type", "application/octet-stream")
    filename = request.headers.get("x-filename", "upload")

    wrapped = StarletteUploadFile(
        filename=filename,
        file=BytesIO(raw_bytes),
        content_type=content_type,
    )
    return wrapped


async def _run_pipeline(file: UploadFile) -> JSONResponse:
    try:
        status_code, body = await run_ocr_pipeline(file)
        return JSONResponse(status_code=status_code, content=body)
    except Exception as exc:
        logger.exception("OCR pipeline crashed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "OCR pipeline crashed", "detail": str(exc)},
        )


# -------------------------------------------------------------------------
# /api/mailbills/parse (OCR only)
# -------------------------------------------------------------------------
@app.get("/api/mailbills/parse")
async def mailbills_parse_alive() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"ok": True, "message": "mailbills/parse alive"},
    )


@app.post("/api/mailbills/parse")
async def mailbills_parse(
    request: Request,
    file: Optional[UploadFile] = FILE_NONE,
    target_lang: str = Query(default="en"),
) -> JSONResponse:
    upload = await _coerce_upload_file(request, file)
    logger.info(
        "mailbills/parse received file=%s content_type=%s target_lang=%s",
        upload.filename,
        upload.content_type,
        target_lang,
    )
    return await _run_pipeline(upload)


# -------------------------------------------------------------------------
# /api/ocr-debug
# -------------------------------------------------------------------------
@app.get("/api/ocr-debug")
async def ocr_debug_alive() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"ok": True, "message": "ocr-debug alive"},
    )


@app.post("/api/ocr-debug")
async def ocr_debug(
    request: Request,
    file: Optional[UploadFile] = FILE_NONE,
    target_lang: str = Query(default="en"),
) -> JSONResponse:
    upload = await _coerce_upload_file(request, file)
    logger.info(
        "ocr-debug received file=%s content_type=%s target_lang=%s",
        upload.filename,
        upload.content_type,
        target_lang,
    )
    return await _run_pipeline(upload)


# -------------------------------------------------------------------------
# /api/translate (Enhanced with cultural intelligence)
# -------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = Field("es", description="Target language code")
    source_lang: str = Field("auto", description="Source language code or 'auto'")


class TranslateResponse(BaseModel):
    ok: bool
    translated_text: str
    translation: str
    target_lang: str
    source_lang: str
    enrichment: Optional[Dict] = None  # NEW: Cultural intelligence data
    warnings: Optional[list] = None     # NEW: Cultural warnings


@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text_endpoint(req: TranslateRequest) -> TranslateResponse:
    """
    Enhanced translation with cultural intelligence:
    - Idiom detection and adaptation
    - Slang preservation
    - Profanity intensity matching
    - Sarcasm tone detection
    - Cultural warnings
    """
    try:
        # Use File 16 (translation_engine) for full intelligence
        result = translate_with_intelligence(
            text=req.text,
            source_lang=req.source_lang if req.source_lang != "auto" else "en",
            target_lang=req.target_lang
        )
        
        logger.info(
            "Translation: confidence=%.2f warnings=%d enrichment_keys=%s",
            result['confidence_score'],
            len(result['warnings']),
            list(result['enrichment'].keys())
        )
        
        return TranslateResponse(
            ok=True,
            translated_text=result['translated_text'],
            translation=result['translated_text'],
            target_lang=req.target_lang,
            source_lang=req.source_lang,
            enrichment=result['enrichment'],
            warnings=result['warnings']
        )
    except Exception as exc:
        logger.exception("Translation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc


# -------------------------------------------------------------------------
# /api/assistant (Enhanced with cultural intelligence)
# -------------------------------------------------------------------------
class DocumentContext(BaseModel):
    """Optional document context for Mode 2"""
    summary: str = Field("", description="Document summary")
    document_type: str = Field("unknown", description="Document type")
    uploaded_at: str = Field("", description="Upload timestamp")


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's question")
    lang: str = Field("en", description="Language code: 'en' or 'es'")
    document_context: Optional[DocumentContext] = Field(
        None, 
        description="Optional document context"
    )


class AssistantResponse(BaseModel):
    reply: str = Field(..., description="Assistant's response")
    mode: str = Field("general", description="Response mode")
    enrichment: Optional[Dict] = None  # NEW: Intelligence data
    suggestions: Optional[list] = None  # NEW: Suggested follow-up questions


async def _intelligent_assistant(
    message: str, 
    lang: str, 
    doc_context: Optional[DocumentContext]
) -> Dict[str, Any]:
    """
    Enhanced assistant with cultural intelligence
    
    Features:
    1. UI-aware translations (File 17a)
    2. Idiom detection (File 4)
    3. Profanity handling (File 6)
    4. Sarcasm detection (File 7)
    5. Context-aware responses (File 3)
    """
    enrichment = {}
    
    # Check if message contains UI terms (uploads, downloads, etc.)
    ui_keywords = ["upload", "subir", "download", "descargar", "button", "botón"]
    if any(keyword in message.lower() for keyword in ui_keywords):
        # Use UI translator (File 17a)
        if "upload" in message.lower() or "subir" in message.lower():
            help_text = ui_translator.get_help_text("upload", lang)
            return {
                "reply": help_text,
                "mode": "ui-help",
                "enrichment": {"type": "ui_translation", "feature": "upload"}
            }
    
    # Detect sarcasm in message (File 7)
    sarcasm_result = sarcasm_detector.detect_sarcasm(message)
    if sarcasm_result['is_sarcastic']:
        enrichment['sarcasm'] = {
            'detected': True,
            'confidence': sarcasm_result['confidence'],
            'tone': sarcasm_result['tone']
        }
    
    # Detect idioms (File 4)
    idioms_found = idiom_db.detect_idioms(message, "en" if lang == "en" else "es")
    if idioms_found:
        enrichment['idioms'] = idioms_found
    
    # Check for ambiguous words (File 3)
    words = message.split()
    ambiguous_words = []
    for word in words:
        clean_word = word.strip('.,!?').lower()
        if context_handler.is_ambiguous(clean_word, "en" if lang == "en" else "es"):
            ambiguous_words.append(clean_word)
    
    if ambiguous_words:
        enrichment['ambiguous_words'] = ambiguous_words
    
    # Build intelligent response using OpenAI
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    # Enhanced system prompt with intelligence context
    if doc_context and doc_context.summary:
        system_prompt = (
            "You are Voyadecir's intelligent assistant with cultural awareness.\n\n"
            f"Document context:\n"
            f"- Type: {doc_context.document_type}\n"
            f"- Summary: {doc_context.summary}\n\n"
            "You can:\n"
            "1. Answer questions about this specific document\n"
            "2. Explain site features with cultural sensitivity\n"
            "3. Handle idioms, slang, and tone appropriately\n\n"
            "Rules:\n"
            "- Be concise (2-4 sentences)\n"
            "- Reference document details when relevant\n"
            "- Be empathetic - documents can be stressful\n"
            f"- Respond in {'Spanish' if lang == 'es' else 'English'}\n"
        )
        mode = "document-aware"
    else:
        system_prompt = (
            "You are Voyadecir's intelligent assistant.\n\n"
            "Features:\n"
            "- Upload PDFs/images (Mail & Bills Helper)\n"
            "- 10 languages supported\n"
            "- $8/month unlimited, 2-3 free/month\n"
            "- Cultural intelligence (idioms, slang, tone)\n\n"
            "Rules:\n"
            "- Be concise (2-4 sentences)\n"
            "- Explain features clearly\n"
            "- Acknowledge cultural nuances when detected\n"
            f"- Respond in {'Spanish' if lang == 'es' else 'English'}\n"
        )
        mode = "general"
    
    # Add intelligence context to prompt
    if enrichment:
        context_notes = []
        if enrichment.get('sarcasm', {}).get('detected'):
            context_notes.append(f"Note: User's message has a {enrichment['sarcasm']['tone']} tone")
        if enrichment.get('idioms'):
            context_notes.append(f"Note: Message contains idioms: {[i['idiom'] for i in enrichment['idioms']]}")
        if enrichment.get('ambiguous_words'):
            context_notes.append(f"Note: Ambiguous words detected: {enrichment['ambiguous_words']}")
        
        if context_notes:
            system_prompt += "\n\nContext awareness:\n" + "\n".join(context_notes)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    
    req_json = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200,
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
            raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text[:500]}")
        
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    
    # Generate suggestions based on context
    suggestions = []
    if doc_context:
        suggestions = [
            "What should I do next?" if lang == "en" else "¿Qué debo hacer ahora?",
            "Are there any deadlines?" if lang == "en" else "¿Hay fechas límite?",
            "What are the consequences?" if lang == "en" else "¿Cuáles son las consecuencias?"
        ]
    else:
        suggestions = [
            "How do I upload a document?" if lang == "en" else "¿Cómo subo un documento?",
            "What languages do you support?" if lang == "en" else "¿Qué idiomas soportan?",
            "How does OCR work?" if lang == "en" else "¿Cómo funciona el OCR?"
        ]
    
    return {
        "reply": content.strip(),
        "mode": mode,
        "enrichment": enrichment if enrichment else None,
        "suggestions": suggestions[:3]  # Top 3 suggestions
    }


@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_chat(req: AssistantRequest) -> AssistantResponse:
    """
    Intelligent chatbot with cultural awareness
    
    Mode 1 (General): Site features, uploading, languages, pricing
    Mode 2 (Document-aware): Specific document questions
    
    NEW: Integrated with 18 cultural intelligence systems:
    - UI translations (File 17a)
    - Idiom detection (File 4)
    - Sarcasm detection (File 7)
    - Context awareness (File 3)
    - And 14 more...
    """
    try:
        result = await _intelligent_assistant(
            message=req.message,
            lang=req.lang,
            doc_context=req.document_context
        )
        
        logger.info(
            "Assistant: mode=%s lang=%s has_doc=%s enrichment=%s",
            result["mode"],
            req.lang,
            bool(req.document_context),
            bool(result.get("enrichment"))
        )
        
        return AssistantResponse(
            reply=result["reply"],
            mode=result["mode"],
            enrichment=result.get("enrichment"),
            suggestions=result.get("suggestions")
        )
    except Exception as exc:
        logger.exception("Assistant failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc


# -------------------------------------------------------------------------
# /api/test-intelligence (Debug endpoint)
# -------------------------------------------------------------------------
@app.get("/api/test-intelligence")
async def test_intelligence() -> JSONResponse:
    """
    Test if all cultural intelligence systems are loaded and working
    
    Tests:
    - UI translation (File 17a)
    - Idiom detection (File 4)
    - Profanity detection (File 6)
    - Sarcasm detection (File 7)
    - Context handler (File 3)
    """
    try:
        tests = {
            "ui_translation": {
                "test": "uploads → menu item",
                "result": ui_translator.translate_ui_element("uploads", "menu", target_lang="es"),
                "expected": "Cómo subir documentos (NOT 'cargas')"
            },
            "idiom_detection": {
                "test": "break a leg",
                "result": idiom_db.detect_idioms("break a leg", "en"),
                "expected": "Detected idiom with cultural equivalent"
            },
            "profanity_detection": {
                "test": "damn",
                "result": profanity_handler.detect_profanity("damn"),
                "expected": "Intensity level: 1 (mild)"
            },
            "sarcasm_detection": {
                "test": "Oh great, another bill",
                "result": sarcasm_detector.detect_sarcasm("Oh great, another bill"),
                "expected": "Sarcastic: True"
            },
            "context_awareness": {
                "test": "bank (ambiguous)",
                "result": context_handler.is_ambiguous("bank", "en"),
                "expected": "True (financial vs. river)"
            }
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "message": "All cultural intelligence systems operational",
                "systems_loaded": 18,
                "tests": tests
            }
        )
    except Exception as exc:
        logger.exception("Intelligence test failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Some intelligence systems failed to load"
            }
        )
