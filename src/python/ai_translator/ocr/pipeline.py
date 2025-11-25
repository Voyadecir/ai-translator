import logging
import textwrap
from io import BytesIO
from typing import Dict, List, Tuple

import cv2
import numpy as np
from fastapi import UploadFile
from pdf2image import convert_from_bytes
from PIL import Image, ImageFilter

from ai_translator import config
from ai_translator.ocr.azure_read import azure_read
from ai_translator.ocr.tesseract_fallback import tesseract_ocr
from ai_translator.ocr.types import OcrResult, StageError, build_stage_error_response

logger = logging.getLogger(__name__)


def _ensure_debug_dir():
    if config.DEBUG_SAVE:
        import os

        os.makedirs(config.DEBUG_DIR, exist_ok=True)


def _save_debug_image(image: Image.Image, name: str) -> None:
    if not config.DEBUG_SAVE:
        return
    _ensure_debug_dir()
    path = f"{config.DEBUG_DIR}/{name}"
    image.save(path)


def _open_image(data: bytes) -> Image.Image:
    try:
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:  # pragma: no cover - defensive
        raise StageError("upload_parse", f"Unsupported image format: {exc}")


def _convert_pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300, fmt="png")
    except Exception as exc:
        raise StageError("pdf_to_image", f"Failed to convert PDF: {exc}")
    if not images:
        raise StageError("pdf_to_image", "No pages found in PDF")
    return images


def _deskew(gray: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(gray > 0))
    if coords.size == 0:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _preprocess_image(image: Image.Image, idx: int) -> Image.Image:
    np_img = np.array(image)
    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
    gray = _deskew(gray)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    denoised = cv2.fastNlMeansDenoising(thresh, h=15, templateWindowSize=7, searchWindowSize=21)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    processed = Image.fromarray(sharpened).filter(ImageFilter.MedianFilter(size=3))
    _save_debug_image(processed, f"preprocessed_page_{idx}.png")
    return processed


def preprocess_bytes(
    file_bytes: bytes, content_type: str
) -> Tuple[List[Image.Image], Dict[str, object], str]:
    stages_meta: Dict[str, object] = {}
    if content_type == "application/pdf" or file_bytes.startswith(b"%PDF"):
        images = _convert_pdf_to_images(file_bytes)
        stages_meta["pdf_to_image"] = {"status": "ok", "dpi": 300, "pages": len(images)}
    else:
        images = [_open_image(file_bytes)]
    preprocessed: List[Image.Image] = []
    for idx, img in enumerate(images, start=1):
        preprocessed.append(_preprocess_image(img, idx))
    stages_meta["preprocess"] = "ok"
    stages_meta["preprocess_steps"] = [
        "grayscale",
        "deskew",
        "adaptive_threshold",
        "denoise",
        "sharpen",
    ]
    render_format = "PDF" if len(preprocessed) > 1 or content_type == "application/pdf" else "PNG"
    return preprocessed, stages_meta, render_format


def _images_to_bytes(images: List[Image.Image], render_format: str) -> Tuple[bytes, str]:
    buffer = BytesIO()
    if render_format.upper() == "PDF":
        images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
        content_type = "application/pdf"
    else:
        images[0].save(buffer, format="PNG")
        content_type = "image/png"
    return buffer.getvalue(), content_type


def _build_summary(text: str, confidence: float) -> str:
    text = (text or "").strip()
    preview = textwrap.shorten(text, width=320, placeholder="...") if text else ""
    warnings: List[str] = []
    if confidence < config.CONFIDENCE_THRESHOLD:
        warnings.append(
            "Low confidence OCR; please retake a clear, well-lit photo. / OCR de baja confianza; por favor vuelva a tomar una foto clara y bien iluminada."
        )
    if not text:
        warnings.append("No text extracted. / No se extrajo texto.")
    pieces = []
    if preview:
        pieces.append(f"Preview: {preview}")
    if warnings:
        pieces.extend(warnings)
    return " ".join(pieces)


async def run_ocr_pipeline(file: UploadFile) -> Tuple[int, Dict[str, object]]:
    stages: Dict[str, object] = {}
    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise StageError("upload_parse", "Uploaded file is empty")
        content_type = file.content_type or "application/octet-stream"
        stages["upload_parse"] = {
            "status": "ok",
            "content_type": content_type,
            "size_bytes": len(raw_bytes),
            "filename": file.filename,
            "magic": raw_bytes[:12].hex(),
        }
    except StageError as exc:
        return 400, build_stage_error_response(exc.stage, exc.message, stages)
    except Exception as exc:  # pragma: no cover - defensive
        return 400, build_stage_error_response("upload_parse", str(exc), stages)

    try:
        preprocessed, preprocess_meta, render_format = preprocess_bytes(raw_bytes, content_type)
        stages.update(preprocess_meta)
    except StageError as exc:
        return 400, build_stage_error_response(exc.stage, exc.message, stages)

    payload_bytes, payload_type = _images_to_bytes(preprocessed, render_format)

    azure_result: OcrResult | None = None
    try:
        azure_result = await azure_read(payload_bytes, payload_type, stages)
    except StageError as exc:
        stages["azure_call"] = {"status": "error", "reason": exc.message}
    except Exception as exc:  # pragma: no cover - defensive
        stages["azure_call"] = {"status": "error", "reason": str(exc)}

    final_result: OcrResult
    if azure_result and azure_result.confidence >= config.CONFIDENCE_THRESHOLD:
        final_result = azure_result
        stages["fallback_call"] = "skipped"
    else:
        if azure_result:
            stages["azure_call"] = {
                "status": "ok_but_low_confidence",
                "confidence": round(azure_result.confidence, 3),
                "threshold": config.CONFIDENCE_THRESHOLD,
            }
        stages["fallback_call"] = "running"
        try:
            final_result = tesseract_ocr(preprocessed)
        except StageError as exc:
            return 500, build_stage_error_response(exc.stage, exc.message, stages)
        except Exception as exc:  # pragma: no cover - defensive
            return 500, build_stage_error_response("fallback_call", str(exc), stages)
        stages["fallback_call"] = {"status": "ok", "engine": "tesseract"}

    stages["extraction"] = {
        "status": "ok",
        "engine_used": final_result.engine_used,
        "confidence": round(final_result.confidence, 3),
    }

    raw_text = final_result.text or ""
    translation = raw_text  # placeholder to keep contract without relying on external calls
    summary = _build_summary(raw_text, final_result.confidence)

    response_body = {
        "engine_used": final_result.engine_used,
        "stages": stages,
        "confidence": round(final_result.confidence, 3),
        "raw_text": raw_text,
        "translation": translation,
        "summary": summary,
    }
    return 200, response_body


__all__ = [
    "run_ocr_pipeline",
    "preprocess_bytes",
]
