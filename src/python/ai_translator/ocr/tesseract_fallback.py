from typing import List

import pytesseract
from PIL import Image

from ai_translator.ocr.types import OcrResult, StageError


def tesseract_ocr(images: List[Image.Image]) -> OcrResult:
    """Run Tesseract OCR as a fallback engine."""
    if not images:
        raise StageError("fallback_call", "No preprocessed images provided for fallback")

    texts: List[str] = []
    for img in images:
        try:
            text = pytesseract.image_to_string(
                img,
                lang="eng+spa",
                config="--oem 3 --psm 6",
            )
        except pytesseract.TesseractError as exc:  # pragma: no cover - depends on system binary
            raise StageError("fallback_call", f"Tesseract failed: {exc}")
        texts.append(text)

    combined = "\n".join(texts)
    # Confidence is heuristic for fallback
    return OcrResult(text=combined, confidence=0.55, engine_used="tesseract_fallback")
