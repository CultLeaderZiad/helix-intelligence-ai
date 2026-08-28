import os
import httpx
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        self.model = "gemini-flash-latest"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            raise Exception("GEMINI_API_KEY not configured")
            
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": gemini_messages,
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.2
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
