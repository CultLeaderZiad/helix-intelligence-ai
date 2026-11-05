import json
import logging
from app.core.observability import log_event
from typing import List
from abc import ABC, abstractmethod
from fastapi import HTTPException
from app.schemas.analysis import Insight, Pattern
from app.schemas.creative import Creative
from app.services.ai.prompts import (
    PROMPT_INSIGHT,
    PROMPT_PATTERNS,
    insight_messages,
    pattern_messages,
)
from app.services.ai.structured import (
    parse_insight,
    parse_patterns,
)

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    @abstractmethod
    async def _call_api(self, messages: List[dict]) -> str:
        """Subclasses implement this to call their respective API"""
        pass

    async def generate_insight(self, creative: Creative, context: str = "") -> Insight:
        """Generate an insight for a specific creative.

        Provider failures are never masked: this method raises, callers
        surface an honest "temporarily unavailable" state, and the user
        is not charged. There is deliberately NO fabricated fallback.
        """
        del context
        try:
            result_text = await self._call_api(insight_messages(creative))
            data = _load_json(result_text)
            model_name = getattr(self, "model", None) or "unknown"
            return parse_insight(
                data,
                creative_id=creative.id,
                model_version=f"{model_name}:{PROMPT_INSIGHT}",
            )
        except Exception as exc:
            log_event(logger, "ai_insight_failed", error=exc)
            raise HTTPException(
                status_code=503,
                # Preserve the existing string-detail contract; expose the stable
                # machine code separately without including provider messages.
                detail="AI insight generation is temporarily unavailable.",
                headers={"X-Error-Code": "analysis_unavailable"},
            ) from None
        
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
