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
    allow_methods=["*"],  # GET, POST, OPTIONS, etc
    allow_headers=["*"],  # Content-Type, Authorization, etc
)

# Deep agent routes: /api/mailbills/interpret AND /api/mailbills/translate-pdf
app.include_router(mailbills_router, prefix="/api")

# Ruff B008-friendly: call File() once at module level
FILE_NONE = File(default=None)

# -------------------------------------------------------------------------
# Shared upload helpers (OCR endpoints)
# -------------------------------------------------------------------------
async def _coerce_upload_file(
    request: Request,
    file: Optional[UploadFile],
) -> UploadFile:
    """
    Accept either:
    1) multipart UploadFile (FormData field "file")
    2) raw body upload (Content-Type: application/pdf, image/*, etc)
    """
    if file is not None:
        return file

    raw_bytes = await request.body()
    if not raw_bytes:
        raise HTTPException(
            status_code=400,
            detail="No file provided. Send FormData field 'file' or raw body.",
        )

    content_type = request.headers.get(
        "content-type",
        "application/octet-stream",
    )
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
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR pipeline crashed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "OCR pipeline crashed",
                "detail": str(exc),
            },
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
# /api/translate (text translation proxy used by site + Azure Functions)
# -------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = Field(
        "es",
        description="Target language code, e.g. 'es', 'en', 'fr', etc.",
    )
    source_lang: str = Field(
        "auto",
        description="Optional source language code, or 'auto'.",
    )


class TranslateResponse(BaseModel):
    ok: bool
    translated_text: str
    translation: str
    target_lang: str
    source_lang: str


async def _call_openai_translate(payload: TranslateRequest) -> str:
    """
    Core translation call used by /api/translate.
    Supports any natural-language target (not just English/Spanish).
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured in the environment.")

    system_prompt = (
        "You are a professional translation engine. "
        "Translate the user text into the requested target language.\n"
        "- Preserve the original meaning and important details.\n"
        "- Use natural, professional wording (not word-for-word literal).\n"
        "- Return ONLY the translated text, with no quotes or explanations."
    )

    target = payload.target_lang.strip().lower()

    # Friendly labels for common languages; otherwise just pass the code through.
    if target.startswith("es"):
        target_label = "Spanish"
    elif target.startswith("en"):
        target_label = "English"
    elif target.startswith("pt"):
        target_label = "Portuguese"
    elif target.startswith("fr"):
        target_label = "French"
    elif target.startswith("zh"):
        target_label = "Chinese"
    elif target.startswith("hi"):
        target_label = "Hindi"
    elif target.startswith("ar"):
        target_label = "Arabic"
    elif target.startswith("bn"):
        target_label = "Bengali"
    elif target.startswith("ru"):
        target_label = "Russian"
    elif target.startswith("ur"):
        target_label = "Urdu"
    else:
        target_label = payload.target_lang

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Target language: {target_label}\nText:\n{payload.text}",
        },
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
                f"OpenAI translate error {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected OpenAI translate response: {exc}") from exc

    return content.strip()


@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest) -> TranslateResponse:
    """
    Simple translation endpoint.
    Contract:
      Request JSON: { "text": "...", "target_lang": "es", "source_lang": "auto" }
      Response JSON: { "ok": true, "translated_text": "...", "translation": "..." }
    """
    try:
        translated = await _call_openai_translate(req)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Translation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc

    return TranslateResponse(
        ok=True,
        translated_text=translated,
        translation=translated,  # keep both keys for old frontends
        target_lang=req.target_lang,
        source_lang=req.source_lang,
    )


# -------------------------------------------------------------------------
# /api/assistant (NEW: Chatbot endpoint - Mode 1 & Mode 2)
# -------------------------------------------------------------------------
class DocumentContext(BaseModel):
    """Optional document context for Mode 2 (document-aware responses)"""
    summary: str = Field("", description="Brief summary of the uploaded document")
    document_type: str = Field("unknown", description="Type of document (bill, letter, contract, etc.)")
    uploaded_at: str = Field("", description="ISO timestamp when document was uploaded")


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's question")
    lang: str = Field("en", description="Language code: 'en' or 'es'")
    document_context: Optional[DocumentContext] = Field(
        None, 
        description="Optional: context from recently uploaded document for document-aware responses"
    )


class AssistantResponse(BaseModel):
    reply: str = Field(..., description="Assistant's response")
    mode: str = Field("general", description="Response mode: 'general' or 'document-aware'")


async def _call_openai_assistant(
    message: str, 
    lang: str, 
    doc_context: Optional[DocumentContext]
) -> Dict[str, Any]:
    """
    Call OpenAI for assistant responses.
    
    Mode 1 (General): No document context - answers site questions
    Mode 2 (Document-aware): Has document context - can answer document-specific questions
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured in the environment.")

    # Build system prompt based on mode
    if doc_context and doc_context.summary:
        # Mode 2: Document-aware
        system_prompt = (
            "You are a helpful assistant for Voyadecir, a service that helps people understand "
            "documents, bills, and letters in multiple languages.\n\n"
            "The user recently uploaded a document. Here's what we know about it:\n"
            f"- Type: {doc_context.document_type}\n"
            f"- Summary: {doc_context.summary}\n"
            f"- Uploaded: {doc_context.uploaded_at}\n\n"
            "You can answer questions about:\n"
            "1. This specific document (amounts, dates, what to do next, consequences, etc.)\n"
            "2. General questions about using Voyadecir\n\n"
            "Rules:\n"
            "- Be concise and helpful (2-4 sentences max)\n"
            "- If asked about the document, reference specific details from the summary\n"
            "- If asked about site features, explain clearly\n"
            "- Be empathetic - documents can be stressful for non-native speakers\n"
            f"- Respond in {'Spanish' if lang == 'es' else 'English'}\n"
        )
        mode = "document-aware"
    else:
        # Mode 1: General help
        system_prompt = (
            "You are a helpful assistant for Voyadecir, a service that helps people understand "
            "documents, bills, and letters in multiple languages.\n\n"
            "You can help with:\n"
            "- How to upload documents (PDFs, images)\n"
            "- What languages are supported (English, Spanish, Portuguese, French, Chinese, Hindi, Arabic, Bengali, Russian, Urdu)\n"
            "- Privacy and security questions\n"
            "- Pricing ($8/month for unlimited, 2-3 free scans/month)\n"
            "- How OCR and translation work\n\n"
            "Rules:\n"
            "- Be concise and friendly (2-4 sentences max)\n"
            "- If you don't know something specific, be honest\n"
            "- Encourage users to try the Mail & Bills Helper for document scanning\n"
            f"- Respond in {'Spanish' if lang == 'es' else 'English'}\n"
        )
        mode = "general"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    req_json = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,  # Slightly higher for conversational responses
        "max_tokens": 200,  # Keep responses concise
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
                f"OpenAI assistant error {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected OpenAI assistant response: {exc}") from exc

    return {
        "reply": content.strip(),
        "mode": mode
    }


@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_chat(req: AssistantRequest) -> AssistantResponse:
    """
    Chatbot assistant endpoint.
    
    Mode 1 (General): Answers questions about site features, uploading, languages, pricing
    Mode 2 (Document-aware): Can answer questions about a specific uploaded document
    
    Cost: ~$0.0001-0.0003 per conversation (gpt-4o-mini)
    """
    try:
        result = await _call_openai_assistant(
            message=req.message,
            lang=req.lang,
            doc_context=req.document_context
        )
        
        logger.info(
            "Assistant response: mode=%s lang=%s has_doc_context=%s",
            result["mode"],
            req.lang,
            bool(req.document_context)
        )
        
        return AssistantResponse(
            reply=result["reply"],
            mode=result["mode"]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Assistant failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "message": str(exc)},
        ) from exc
