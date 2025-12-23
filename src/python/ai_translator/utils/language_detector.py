"""Lightweight language detector used when callers request auto-detect.

This wrapper centralizes detection so we can keep the translation engine
untouched.  It favors deterministic output (seeded) and falls back to a
configurable default when detection is uncertain.
"""

from __future__ import annotations

from typing import Tuple

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

# Keep deterministic for repeatable responses
DetectorFactory.seed = 0


def detect_language(text: str, fallback: str = "en") -> Tuple[str, float]:
    """Detect the most likely language from free-form text.

    Args:
        text: Raw user text.
        fallback: Language code to return if detection fails.

    Returns:
        (language_code, confidence_score)
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return fallback, 0.0

    try:
        candidates = detect_langs(cleaned)
        if not candidates:
            return fallback, 0.0

        best = candidates[0]
        lang = best.lang.split("-")[0]
        confidence = float(best.prob)
        return lang, confidence
    except LangDetectException:
        return fallback, 0.0

