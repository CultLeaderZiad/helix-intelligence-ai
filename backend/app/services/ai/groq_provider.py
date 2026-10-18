import os
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class GroqProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            raise Exception("Missing required integration key: GROQ_API_KEY")
        from app.services.ai.call_policy import complete_chat, remember
        result = await complete_chat(
            provider_name="groq",
            url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            fallback_models=["llama-3.1-8b-instant"],
            messages=messages,
            allowed_hosts={"api.groq.com"},
            response_format={"type": "json_object"},
        )
        remember(self, result)
        self.model = f"groq/{result.model}"
        return result.text

