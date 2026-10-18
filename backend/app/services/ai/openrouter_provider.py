import os
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class OpenRouterProvider(AIProvider):
    def __init__(self, trial_mode: bool = False):
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.trial_mode = trial_mode
        self.model = "dots-studio/dots-3-note-preview:free"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            raise Exception("OPENROUTER_API_KEY not configured")
        from app.services.ai.call_policy import complete_chat, remember
        result = await complete_chat(
            provider_name="openrouter",
            url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            allowed_hosts={"openrouter.ai"},
            extra_headers={
                "HTTP-Referer": "https://helixintelligence.ai",
                "X-Title": "Helix Intelligence",
            },
            response_format=None,
        )
        remember(self, result)
        self.model = f"openrouter/{result.model}"
        return result.text
