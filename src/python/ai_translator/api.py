import logging
from typing import Dict, Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from . import config
from .ocr import (
    OcrResult,
    StageError,
    build_stage_error_response,
    call_azure_read,
    preprocess_bytes,
    run_tesseract,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voyadecir OCR Backend")


@app.post("/api/ocr-debug")
async def ocr_debug(file: UploadFile = File(...)):
    stages: Dict[str, object] = {}
    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise StageError("upload_parse", "Uploaded file is empty")
        content_type = file.content_type or ""
        stages["upload_parse"] = {
            "status": "ok",
            "content_type": content_type,
            "size_bytes": len(raw_bytes),
            "filename": file.filename,
            "magic": raw_bytes[:12].hex(),
        }
    except StageError as exc:
        return JSONResponse(status_code=400, content=build_stage_error_response(exc.stage, exc.message, stages))
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(status_code=400, content=build_stage_error_response("upload_parse", str(exc), stages))

    try:
        preprocessed, preprocess_meta, render_format = preprocess_bytes(raw_bytes, content_type)
        stages.update(preprocess_meta)
    except StageError as exc:
        return JSONResponse(status_code=400, content=build_stage_error_response(exc.stage, exc.message, stages))

    payload_bytes, payload_type = _prepare_payload(preprocessed, render_format)

    try:
        azure_result: Optional[OcrResult] = None
        try:
            azure_result = await call_azure_read(payload_bytes, payload_type, stages)
        except StageError as exc:
            stages["azure_read_call"] = {"status": "error", "reason": exc.message}
        except Exception as exc:  # pragma: no cover - defensive
            stages["azure_read_call"] = {"status": "error", "reason": str(exc)}

        final_result: OcrResult
        if azure_result and azure_result.confidence >= config.CONFIDENCE_THRESHOLD:
            final_result = azure_result
            stages["fallback_call"] = "skipped"
        else:
            if azure_result:
                stages["azure_read_call"] = {
                    "status": "ok_but_low_confidence",
                    "confidence": azure_result.confidence,
                    "threshold": config.CONFIDENCE_THRESHOLD,
                }
            stages["fallback_call"] = "running"
            try:
                final_result = run_tesseract(preprocessed)
            except StageError as exc:
                return JSONResponse(status_code=500, content=build_stage_error_response(exc.stage, exc.message, stages))
            except Exception as exc:  # pragma: no cover - defensive
                return JSONResponse(status_code=500, content=build_stage_error_response("fallback_call", str(exc), stages))
            stages["fallback_call"] = "ok"

        text_preview = (final_result.text or "").strip().replace("\n", " ")
        if len(text_preview) > 200:
            text_preview = text_preview[:200] + "..."

        response_body = {
            "engine_used": final_result.engine_used,
            "stages": stages,
            "confidence": round(final_result.confidence, 3),
            "text_preview": text_preview,
            "full_text": final_result.text,
        }
        return JSONResponse(status_code=200, content=response_body)
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(status_code=500, content=build_stage_error_response("unexpected", str(exc), stages))


def _prepare_payload(preprocessed, render_format: str):
    from .ocr import _images_to_bytes

    payload_bytes, payload_type = _images_to_bytes(preprocessed, render_format)
    return payload_bytes, payload_type
