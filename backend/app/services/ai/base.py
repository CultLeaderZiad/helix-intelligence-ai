import json
import logging
from app.core.observability import log_event
from typing import List
from abc import ABC, abstractmethod
from fastapi import HTTPException
from app.schemas.analysis import Pattern
from app.schemas.creative import Creative
from app.services.ai.prompts import (
    PROMPT_PATTERNS,
    pattern_messages,
)
from app.services.ai.structured import (
    parse_patterns,
)

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    @abstractmethod
    async def _call_api(self, messages: List[dict]) -> str:
        """Subclasses implement this to call their respective API"""
        pass

        
    async def generate_patterns(self, creatives: List[Creative]) -> List[Pattern]:
        """Extract patterns across multiple creatives"""
        try:
            result_text = await self._call_api(pattern_messages(creatives))
            data = _load_json(result_text)
            model_name = getattr(self, "model", None) or "unknown"
            return parse_patterns(
                data,
                allowed_ids=[c.id for c in creatives],
                model_version=f"{model_name}:{PROMPT_PATTERNS}",
            )
        except Exception as exc:
            log_event(logger, "ai_patterns_invalid_output", error=exc)
            raise HTTPException(status_code=503, detail={
                "code": "analysis_unavailable",
                "message": "AI pattern generation returned an invalid response.",
            }) from None



def _load_json(result_text: str):
    text = result_text or ""
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    data = json.loads(text)
    return data
