import asyncio
import logging
from typing import Dict, List, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_translator import config
from ai_translator.ocr.types import OcrResult, StageError

logger = logging.getLogger(__name__)


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    data: bytes,
    params: Optional[Dict[str, str]] = None,
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


def _compute_confidence(analyze_result: Dict[str, object]) -> float:
    pages = analyze_result.get("pages", []) if isinstance(analyze_result, dict) else []
    confidences: List[float] = []
    for page in pages:
        for word in page.get("words", []):
            conf = word.get("confidence")
            if conf is not None:
                confidences.append(conf)
    if not confidences:
        return 0.0
    return float(sum(confidences) / len(confidences))


def _extract_azure_error(payload: Dict[str, object]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        inner = error.get("innererror") if isinstance(error.get("innererror"), dict) else None
        if inner and inner.get("message"):
            return f"{message}: {inner.get('message')}" if message else str(inner.get("message"))
        if message:
            return str(message)
    analyze_result = payload.get("analyzeResult") if isinstance(payload, dict) else None
    if isinstance(analyze_result, dict):
        errors = analyze_result.get("errors")
        if isinstance(errors, list) and errors:
            messages = [
                err.get("message") for err in errors if isinstance(err, dict) and err.get("message")
            ]
            if messages:
                return "; ".join(messages)
    return "Unknown error"


async def azure_read(file_bytes: bytes, content_type: str, stages: Dict[str, object]) -> OcrResult:
    if config.OFFLINE_MODE:
        raise StageError("azure_call", "Offline mode enabled")

    required_fields = {
        "AZURE_DI_ENDPOINT": config.AZURE_DI_ENDPOINT,
        "AZURE_DI_API_KEY": config.AZURE_DI_API_KEY,
        "AZURE_DI_API_VERSION": config.AZURE_DI_API_VERSION,
        "AZURE_DI_MODEL": config.AZURE_DI_MODEL,
    }
    missing = [name for name, value in required_fields.items() if not value]
    if missing:
        raise StageError(
            "azure_call",
            f"Missing Azure Document Intelligence configuration: {', '.join(sorted(missing))}",
        )

    base_endpoint = config.AZURE_DI_ENDPOINT.rstrip("/")
    analyze_url = "/".join(
        [
            base_endpoint,
            "documentintelligence",
            "documentModels",
            f"{config.AZURE_DI_MODEL}:analyze",
        ]
    )
    params = {"api-version": config.AZURE_DI_API_VERSION}
    headers = {
        "Ocp-Apim-Subscription-Key": config.AZURE_DI_API_KEY,
        "Content-Type": content_type,
        "Accept": "application/json",
    }

    stages["azure_call"] = {
        "status": "calling",
        "endpoint": base_endpoint,
        "model": config.AZURE_DI_MODEL,
    }

    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT_SECONDS, follow_redirects=True
    ) as client:
        try:
            analyze_response = await _post_with_retry(
                client, analyze_url, headers, file_bytes, params=params
            )
        except RetryError as exc:
            reason = str(exc.last_attempt.exception()) if exc.last_attempt else str(exc)
            raise StageError("azure_call", f"Azure analyze failed after retries: {reason}")
        except httpx.HTTPError as exc:
            raise StageError("azure_call", f"Azure analyze failed: {exc}")

        operation_url = analyze_response.headers.get(
            "operation-location"
        ) or analyze_response.headers.get("Operation-Location")
        if not operation_url:
            raise StageError("azure_call", "Missing Operation-Location header from Azure response")

        poll_headers = {
            "Ocp-Apim-Subscription-Key": config.AZURE_DI_API_KEY,
            "Accept": "application/json",
        }
        delay = config.AZURE_DI_INITIAL_POLL_WAIT
        for attempt in range(1, config.AZURE_DI_POLL_ATTEMPTS + 1):
            await asyncio.sleep(delay)
            try:
                poll = await client.get(operation_url, headers=poll_headers, params=params)
                poll.raise_for_status()
            except httpx.HTTPError as exc:
                raise StageError("azure_call", f"Azure poll failed on attempt {attempt}: {exc}")

            payload = poll.json()
            status = (payload.get("status") or "").lower()
            if status == "succeeded":
                analyze_result = payload.get("analyzeResult", {})
                text = analyze_result.get("content", "")
                confidence = _compute_confidence(analyze_result)
                stages["azure_call"] = {
                    "status": "ok",
                    "operation_url": operation_url,
                    "poll_attempts": attempt,
                    "api_version": config.AZURE_DI_API_VERSION,
                    "confidence": round(confidence, 3),
                }
                return OcrResult(text=text, confidence=confidence, engine_used="azure_primary")
            if status in {"failed", "canceled"}:
                message = _extract_azure_error(payload)
                raise StageError("azure_call", f"Azure OCR {status}: {message}")

            delay = min(delay * config.AZURE_DI_POLL_BACKOFF, config.AZURE_DI_MAX_POLL_WAIT)

        raise StageError(
            "azure_call",
            f"Azure OCR timed out while polling ({config.AZURE_DI_POLL_ATTEMPTS} attempts)",
        )
