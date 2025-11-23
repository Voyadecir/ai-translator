import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import cv2
import httpx
import numpy as np
import pytesseract
from PIL import Image, ImageFilter
from pdf2image import convert_from_bytes
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential

from . import config

logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    text: str
    confidence: float
    engine_used: str


class StageError(Exception):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message


def _ensure_debug_dir():
    if config.DEBUG_SAVE:
        import os

        os.makedirs(config.DEBUG_DIR, exist_ok=True)


def _save_debug_image(image: Image.Image, name: str) -> Optional[str]:
    if not config.DEBUG_SAVE:
        return None
    _ensure_debug_dir()
    path = f"{config.DEBUG_DIR}/{name}"
    image.save(path)
    return path


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
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    denoised = cv2.fastNlMeansDenoising(thresh, h=15, templateWindowSize=7, searchWindowSize=21)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    processed = Image.fromarray(sharpened).filter(ImageFilter.MedianFilter(size=3))
    _save_debug_image(processed, f"preprocessed_page_{idx}.png")
    return processed


def preprocess_bytes(file_bytes: bytes, content_type: str) -> Tuple[List[Image.Image], Dict[str, object], str]:
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
    stages_meta["preprocess_steps"] = ["grayscale", "deskew", "adaptive_threshold", "denoise", "sharpen"]
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


async def _post_with_retry(
    client: httpx.AsyncClient, url: str, headers: Dict[str, str], data: bytes, params: Optional[Dict[str, str]] = None
) -> httpx.Response:
    async for attempt in AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
    ):
        with attempt:
            response = await client.post(url, headers=headers, content=data, params=params)
            response.raise_for_status()
            return response
    raise RuntimeError("Unreachable retry block")


async def call_azure_read(file_bytes: bytes, content_type: str, stages: Dict[str, object]) -> OcrResult:
    if config.OFFLINE_MODE:
        raise StageError("azure_read_call", "Offline mode enabled")
    if not (config.AZURE_DI_ENDPOINT and config.AZURE_DI_API_KEY):
        raise StageError("azure_read_call", "Missing Azure Document Intelligence configuration")

    analyze_url = f"{config.AZURE_DI_ENDPOINT}/documentintelligence/documentModels/{config.AZURE_DI_MODEL}:analyze"
    params = {"api-version": config.AZURE_DI_API_VERSION}
    headers = {
        "Ocp-Apim-Subscription-Key": config.AZURE_DI_API_KEY,
        "Content-Type": content_type,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_SECONDS) as client:
        try:
            analyze_response = await _post_with_retry(client, analyze_url, headers, file_bytes, params=params)
        except RetryError as exc:
            raise StageError("azure_read_call", f"Azure analyze failed after retries: {exc}")
        except httpx.HTTPError as exc:
            raise StageError("azure_read_call", f"Azure analyze failed: {exc}")

        operation_url = analyze_response.headers.get("operation-location") or analyze_response.headers.get("Operation-Location")
        if not operation_url:
            raise StageError("azure_read_call", "Missing Operation-Location header from Azure response")

        for attempt in range(10):
            await asyncio.sleep(min(1 + attempt * 0.5, 4))
            poll = await client.get(
                operation_url,
                headers={"Ocp-Apim-Subscription-Key": config.AZURE_DI_API_KEY, "Accept": "application/json"},
                params=params,
            )
            poll.raise_for_status()
            payload = poll.json()
            status = payload.get("status")
            if status == "succeeded":
                analyze_result = payload.get("analyzeResult", {})
                text = analyze_result.get("content", "")
                confidence = _compute_confidence(analyze_result)
                stages["azure_read_call"] = "ok"
                return OcrResult(text=text, confidence=confidence, engine_used="azure_primary")
            if status in {"failed", "canceled"}:
                raise StageError("azure_read_call", f"Azure OCR {status}")
        raise StageError("azure_read_call", "Azure OCR timed out while polling")


def _compute_confidence(analyze_result: Dict[str, object]) -> float:
    pages = analyze_result.get("pages", [])
    confidences: List[float] = []
    for page in pages:
        for word in page.get("words", []):
            conf = word.get("confidence")
            if conf is not None:
                confidences.append(conf)
    if not confidences:
        return 0.0
    return float(sum(confidences) / len(confidences))


def run_tesseract(images: List[Image.Image]) -> OcrResult:
    texts: List[str] = []
    for img in images:
        try:
            text = pytesseract.image_to_string(img, lang="eng+spa", config="--oem 3 --psm 6")
        except pytesseract.TesseractError as exc:  # pragma: no cover - depends on system binary
            raise StageError("fallback_call", f"Tesseract failed: {exc}")
        texts.append(text)
    combined = "\n".join(texts)
    return OcrResult(text=combined, confidence=0.5, engine_used="fallback")


def build_stage_error_response(stage: str, message: str, stages: Dict[str, object]) -> Dict[str, object]:
    stages[stage] = {"status": "error", "reason": message}
    return {
        "engine_used": None,
        "stages": stages,
        "confidence": 0.0,
        "text_preview": "",
        "error_stage": stage,
        "error_message": message,
    }


__all__ = [
    "OcrResult",
    "StageError",
    "preprocess_bytes",
    "run_tesseract",
    "call_azure_read",
    "build_stage_error_response",
    "_images_to_bytes",
]
