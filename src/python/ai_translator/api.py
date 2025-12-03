import logging
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import UploadFile as StarletteUploadFile

from .ocr import run_ocr_pipeline
from .mailbills_agent import router as mailbills_router  # deep agent router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Voyadecir OCR + MailBills Backend")

# ✅ CORS: allow your production site(s) to call this API
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # allow GET, POST, OPTIONS, etc
    allow_headers=["*"],   # allow Content-Type, Authorization, etc
)

# ✅ Include deep agent routes under /api/mailbills/interpret, etc.
app.include_router(mailbills_router, prefix="/api")

# Ruff B008-friendly: call File() once at module level
FILE_NONE = File(default=None)


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
    except Exception as exc:
        logger.exception("OCR pipeline crashed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "OCR pipeline crashed",
                "detail": str(exc),
            },
        )


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
