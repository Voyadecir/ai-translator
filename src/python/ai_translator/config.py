import os
from typing import Optional


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


AZURE_DI_ENDPOINT: Optional[str] = os.getenv("AZURE_DI_ENDPOINT")
AZURE_DI_API_KEY: Optional[str] = os.getenv("AZURE_DI_API_KEY")
AZURE_DI_API_VERSION: str = os.getenv("AZURE_DI_API_VERSION", "2024-07-31")
AZURE_DI_MODEL: str = os.getenv("AZURE_DI_MODEL", "prebuilt-read")
HTTP_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
OFFLINE_MODE: bool = get_env_bool("OFFLINE_MODE", False)
CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.75"))
DEBUG_SAVE: bool = get_env_bool("OCR_DEBUG_SAVE", False)
DEBUG_DIR: str = os.getenv("OCR_DEBUG_DIR", "/tmp/ocr_debug")
AZURE_DI_POLL_ATTEMPTS: int = int(os.getenv("AZURE_DI_POLL_ATTEMPTS", "10"))
AZURE_DI_INITIAL_POLL_WAIT: float = float(os.getenv("AZURE_DI_INITIAL_POLL_WAIT", "0.5"))
AZURE_DI_MAX_POLL_WAIT: float = float(os.getenv("AZURE_DI_MAX_POLL_WAIT", "4.0"))
AZURE_DI_POLL_BACKOFF: float = float(os.getenv("AZURE_DI_POLL_BACKOFF", "1.5"))
