from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Union
import urllib.request
import urllib.error


# --------------------------------------------------------
# Config object (kept so old code doesn't break)
# --------------------------------------------------------
@dataclass
class TranslationConfig:
    target_lang: str
    timeout: int = 30


# --------------------------------------------------------
# Helper: call OpenAI's API using urllib (no extra deps)
# --------------------------------------------------------
def _openai_translate(text: str, target_lang: str, timeout: int = 30) -> str:
    """
    Call OpenAI API to translate text into target_lang.
    We keep it simple: system prompt + user text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # no key? return fallback
        return f"[{target_lang}] {text}"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # You can change the model if you have a better one on your account
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a translation assistant. "
                    "Translate the user's text into the exact target language. "
                    "Return ONLY the translated text, no explanations."
                ),
            },
            {
                "role": "user",
                "content": f"Translate this into {target_lang}:\n{text}",
            },
        ],
        "temperature": 0.2,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            return parsed["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        # If OpenAI says no (bad key, no credit, etc), fall back
        return f"[{target_lang}] {text} (openai error: {e.code})"
    except Exception as e:
        # any other network error: fallback
        return f"[{target_lang}] {text} (error: {str(e)})"


# --------------------------------------------------------
# Public function – try to be backward compatible
# --------------------------------------------------------
def translate_text(text: str, cfg_or_lang: Union[TranslationConfig, str, None] = None) -> str:
    """
    Main entry point used by your FastAPI app.

    Supports BOTH:
        translate_text("Hello", "es")
    and:
        translate_text("Hello", TranslationConfig("es"))

    If no key or API fails, returns a simple fallback.
    """
    # no text
    if not text or not text.strip():
      return ""

    # figure out target language
    if isinstance(cfg_or_lang, TranslationConfig):
        target_lang = cfg_or_lang.target_lang
        timeout = cfg_or_lang.timeout
    elif isinstance(cfg_or_lang, str):
        target_lang = cfg_or_lang
        timeout = 30
    else:
        # default to Spanish
        target_lang = "es"
        timeout = 30

    # finally try OpenAI
    return _openai_translate(text, target_lang, timeout)


__all__ = ["translate_text", "TranslationConfig"]
