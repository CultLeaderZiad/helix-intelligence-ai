import httpx
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
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Helix Intelligence AI"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
