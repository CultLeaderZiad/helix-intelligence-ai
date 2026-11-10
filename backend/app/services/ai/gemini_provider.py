import os
import logging
from typing import List, Optional
from app.services.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        raw_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY", "")
        self.api_key = raw_key.strip().strip('"\'') if raw_key else ""
        self.model = getattr(settings, "GEMINI_TEXT_MODEL", None) or "gemini-flash-latest"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


    async def _call_api(self, messages: List[dict]) -> str:
        if not self.is_configured:
            raise Exception("GEMINI_API_KEY not configured")
            
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        from app.core.config import settings as _settings
        from app.services.ai.call_policy import ChatResult, remember
        from app.services.safe_fetch import safe_request_async
        token_cap = int(getattr(_settings, "AI_MAX_OUTPUT_TOKENS", 1024) or 1024)
        response = await safe_request_async(
            "POST",
            self.base_url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            json={
                "contents": gemini_messages,
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                    "maxOutputTokens": token_cap,
                },
            },
            timeout=float(getattr(_settings, "AI_CALL_TIMEOUT_S", 20) or 20),
            allowed_hosts={"generativelanguage.googleapis.com"},
        )
        if response.status_code != 200:
            raise Exception(f"Gemini API returned HTTP {response.status_code}")
        data = response.json()
        usage = data.get("usageMetadata") or {}
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")
        total = usage.get("totalTokenCount")
        observed = total is not None
        remember(self, ChatResult(
            text=text,
            provider="gemini",
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            latency_ms=0,
            cost_usd=None,
            tokens_observed=bool(observed),
        ))
        return text

