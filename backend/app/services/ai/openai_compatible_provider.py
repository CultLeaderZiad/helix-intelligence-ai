import os
import httpx
from typing import List, Optional
from app.services.ai.base import AIProvider

class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, default_model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = default_model
        
    async def _call_api(self, messages: List[dict]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": messages
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI-Compatible API error: {response.text}")
                
            result = response.json()
            return result["choices"][0]["message"]["content"]
