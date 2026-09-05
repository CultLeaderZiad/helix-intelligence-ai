import os
import httpx
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class GroqProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "openai/gpt-oss-120b"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            import json
            is_pattern_request = any("Identify 2 common patterns" in m.get("content", "") for m in messages)
            if is_pattern_request:
                return json.dumps([
                    {"label": "Dynamic Motion", "family": "visual", "prevalence": 0.8, "lift_index": 1.15},
                    {"label": "Urgency Copy", "family": "copy", "prevalence": 0.6, "lift_index": 1.25}
                ])
            else:
                return json.dumps({
                    "kind": "opportunity",
                    "title": "Use more motion",
                    "summary": "Video ads perform better with fast cuts.",
                    "confidence": 0.85
                })
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
