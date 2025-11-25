from dataclasses import dataclass
from typing import Dict, Optional


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


def build_stage_error_response(
    stage: str, message: str, stages: Dict[str, object]
) -> Dict[str, object]:
    stages[stage] = {"status": "error", "reason": message}
    return {
        "engine_used": None,
        "stages": stages,
        "confidence": 0.0,
        "raw_text": "",
        "translation": "",
        "summary": "",
        "error_stage": stage,
        "error_message": message,
    }
