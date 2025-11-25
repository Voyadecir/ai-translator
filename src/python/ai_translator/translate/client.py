from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# -----------------------------
# Config + Exceptions
# -----------------------------
@dataclass
class TranslationConfig:
    target_lang: str
    timeout: float = 15.0


class TransientHTTPError(Exception):
    """Network/provider hiccup that is worth retrying."""

    pass


# -----------------------------
# Provider call
# -----------------------------
async def _openai_translate(text: str, target_lang: str, timeout: float) -> str:
    """
    Minimal OpenAI chat call for translation.
    Uses GPT-4o-mini by default. Outputs ONLY the translated text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # no key → predictable fallback
        return f"[{target_lang}] {text}"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional translator. Keep meaning, tone, and "
                    "formatting. Output only the translated text."
                ),
            },
            {"role": "user", "content": f"Translate to {target_lang}:\n\n{text}"},
        ],
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=payload)
        # retry on 5xx, not on most 4xx
        if resp.status_code >= 500:
            raise TransientHTTPError(f"OpenAI {resp.status_code}: {resp.text}")
        if resp.status_code >= 400:
            # surface the body; caller will fallback upstack
            raise RuntimeError(f"OpenAI {resp.status_code}: {resp.text}")

        data = resp.json()
        out = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not out:
            raise RuntimeError("Empty translation from provider")
        return out


# -----------------------------
# Public API
# -----------------------------
@retry(
    stop=stop_after_attempt(int(os.getenv("MAX_RETRIES", "2"))),
    wait=wait_exponential(multiplier=float(os.getenv("RETRY_BACKOFF_SECONDS", "0.8")), max=6),
    retry=retry_if_exception_type(TransientHTTPError),
    reraise=True,
)
async def translate_text(text: str, target_lang: str) -> str:
    """
    Translate given text to target_lang.
    Strategy:
      1) If OFFLINE_MODE=true → mock translation.
      2) If OPENAI_API_KEY present → use OpenAI.
      3) Last resort → bracketed echo.
    """
    text = (text or "").strip()
    if not text:
        return ""

    if os.getenv("OFFLINE_MODE", "false").lower() == "true":
        return f"[{target_lang}] {text}"

    if os.getenv("OPENAI_API_KEY"):
        return await _openai_translate(
            text, target_lang, timeout=float(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
        )

    return f"[{target_lang}] {text}"
