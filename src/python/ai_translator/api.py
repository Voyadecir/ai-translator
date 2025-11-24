import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from .ocr import run_ocr_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voyadecir OCR Backend")


async def _run_pipeline(file: UploadFile) -> JSONResponse:
    status_code, body = await run_ocr_pipeline(file)
    return JSONResponse(status_code=status_code, content=body)


@app.post("/api/mailbills/parse")
async def mailbills_parse(file: UploadFile = File(...)) -> JSONResponse:
    return await _run_pipeline(file)


@app.post("/api/ocr-debug")
async def ocr_debug(file: UploadFile = File(...)) -> JSONResponse:
    return await _run_pipeline(file)
