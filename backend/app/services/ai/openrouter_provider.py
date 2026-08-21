import httpx
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class OpenRouterProvider(AIProvider):
    def __init__(self, trial_mode: bool = False):
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", None)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.trial_mode = trial_mode
        # In trial mode, we should only use models ending in :free (e.g. meta-llama/llama-3-8b-instruct:free)
        self.model = "meta-llama/llama-3-8b-instruct:free" if trial_mode else "anthropic/claude-3-haiku"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            raise Exception("OPENROUTER_API_KEY not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5173", # Optional but recommended by OR
                    "X-Title": "Helixa Intelligence"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
