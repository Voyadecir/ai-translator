import os
import logging
from io import BytesIO
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
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
    allow_methods=["*"],   # GET, POST, OPTIONS, etc
    allow_headers=["*"],   # Content-Type, Authorization, etc
)

# Deep agent routes: /api/mailbills/interpret
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
# /api/mailbills/parse  (OCR only)
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
# /api/translate  (text translation proxy used by site + Azure Functions)
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
    Core translation call used by both /api/translate and the PDF export helper.
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


async def _translate_large_text(text: str, target_lang: str) -> str:
    """
    Helper for long documents (auto policies, contracts, multi-page PDFs).
    Splits the text into manageable chunks and calls OpenAI sequentially.
    """
    text = (text or "").strip()
    if not text:
        return ""

    CHUNK_SIZE = 6000  # characters – conservative; adjust if needed

    if len(text) <= CHUNK_SIZE:
        req = TranslateRequest(text=text, target_lang=target_lang, source_lang="auto")
        return await _call_openai_translate(req)

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end

    translated_chunks = []
    for idx, chunk in enumerate(chunks, start=1):
        logger.info("Translating chunk %s/%s for PDF export", idx, len(chunks))
        req = TranslateRequest(text=chunk, target_lang=target_lang, source_lang="auto")
        translated = await _call_openai_translate(req)
        translated_chunks.append(translated)

    return "\n\n".join(translated_chunks)


def _build_simple_pdf_from_text(translated_text: str) -> bytes:
    """
    Very simple PDF generator for the fully translated document.

    It does NOT perfectly match the original layout yet – it produces a clean,
    multi-page PDF with the translated text, wrapped to a readable width.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # noqa: BLE001
        raise RuntimeError(
            "reportlab is required for PDF export. "
            "Add 'reportlab' to requirements.txt and redeploy."
        ) from exc

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    left_margin = 72  # 1 inch
    right_margin = 72
    top_margin = 72
    bottom_margin = 72
    usable_width = width - left_margin - right_margin
    line_height = 14

    # Crude wrapping based on character count; good enough for a first pass.
    max_chars_per_line = 95

    def wrap_line(text_line: str) -> list[str]:
        words = text_line.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if len(candidate) > max_chars_per_line:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
        return lines

    y = height - top_margin

    for paragraph in translated_text.splitlines():
        # Blank line → add some vertical space
        if not paragraph.strip():
            y -= line_height
            if y < bottom_margin:
                c.showPage()
                y = height - top_margin
            continue

        for line in wrap_line(paragraph):
            if y < bottom_margin:
                c.showPage()
                y = height - top_margin
            c.drawString(left_margin, y, line)
            y -= line_height

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


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
# /api/mailbills/translate-pdf  (multi-page → full translated PDF)
# -------------------------------------------------------------------------


@app.post("/api/mailbills/translate-pdf")
async def mailbills_translate_pdf(
    files: list[UploadFile] = File(..., description="One or more PDF/image files."),
    target_lang: str = Form("es"),
    translation_style: str = Form(
        "professional",
        description=(
            "For future use. Currently always uses professional, non-simplified translation."
        ),
    ),
) -> StreamingResponse:
    """
    New endpoint for the Mail & Bills Helper "Download translated PDF" button.

    - Accepts one *or more* files (PDFs or images) as a single logical document.
    - Runs them through the existing OCR pipeline.
    - Concatenates all extracted text (in page order).
    - Translates the *full* document into the requested language.
    - Returns a cleaned multi-page PDF with the translated text.

    NOTE: For now, this focuses on professional, human-like translation wording.
    The ELI5 explanation remains in /api/mailbills/interpret and is shown
    in the on-screen summary box.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded. Send at least one file under form field 'files'.",
        )

    # Combine OCR text from all uploaded files
    all_text_fragments: list[str] = []

    for idx, upload in enumerate(files, start=1):
        logger.info(
            "translate-pdf OCR file %s (%s) [%s/%s]",
            upload.filename,
            upload.content_type,
            idx,
            len(files),
        )
        status_code, body = await run_ocr_pipeline(upload)
        if status_code >= 300:
            logger.warning(
                "OCR pipeline returned %s for file %s; skipping this file.",
                status_code,
                upload.filename,
            )
            continue

        # Be liberal about where the text might live in the OCR response
        text_piece = (
            (body or {}).get("full_text")
            or (body or {}).get("ocr_text")
            or (body or {}).get("ocr_text_snippet")
            or (body or {}).get("message")
            or ""
        )

        if text_piece and text_piece.strip():
            prefix = ""
            if len(files) > 1:
                prefix = f"\n\n--- Page {idx} ---\n\n"
            all_text_fragments.append(prefix + text_piece.strip())

    combined_text = "\n".join(all_text_fragments).strip()
    if not combined_text:
        raise HTTPException(
            status_code=400,
            detail="No readable text was extracted from the uploaded files.",
        )

    # Translate the entire document in one go (chunked under the hood).
    try:
        translated = await _translate_large_text(combined_text, target_lang)
    except Exception as exc:  # noqa: BLE001
        logger.exception("PDF translation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {exc}",
        ) from exc

    if not translated:
        raise HTTPException(
            status_code=500,
            detail="Translation succeeded but returned empty text.",
        )

    # Build a simple, cleaned PDF from the translated text.
    try:
        pdf_bytes = _build_simple_pdf_from_text(translated)
    except Exception as exc:  # noqa: BLE001
        logger.exception("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="voyadecir-translated-document.pdf"'
        },
    )
