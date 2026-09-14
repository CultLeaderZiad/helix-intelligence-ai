import os
import httpx
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class GroqProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            raise Exception("GROQ_API_KEY not configured")
            
        models_to_try = [self.model, "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        last_err = None

        for m in models_to_try:
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": m,
                            "messages": messages,
                            "response_format": {"type": "json_object"},
                            "temperature": 0.2,
                            "stream": False
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        self.model = m
                        return data["choices"][0]["message"]["content"]
                    else:
                        last_err = f"Groq {m} returned {response.status_code}: {response.text[:150]}"
            except Exception as e:
                last_err = str(e)
                continue

        raise Exception(f"Groq API call failed: {last_err}")

