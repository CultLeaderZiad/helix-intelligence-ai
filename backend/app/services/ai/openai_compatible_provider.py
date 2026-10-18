from typing import List
from urllib.parse import urlsplit
from app.services.ai.base import AIProvider

class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, default_model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = default_model
        
    async def _call_api(self, messages: List[dict]) -> str:
        from app.services.ai.call_policy import complete_chat, remember
        host = (urlsplit(self.base_url).hostname or "").lower()
        result = await complete_chat(
            provider_name=host or "openai-compatible",
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            allowed_hosts={host} if host else None,
        )
        remember(self, result)
        return result.text
