import httpx
from typing import List
from app.services.ai.base import AIProvider
from app.core.config import settings

class GroqProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", None)
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        
    async def _call_api(self, messages: List[dict]) -> str:
        if not self.api_key:
            import json
            # Dummy JSON block to simulate an AI response without a key
            return json.dumps({
                "creatives": [
                    {
                        "brand_name": "Nike (Mocked without API Key)",
                        "product_name": "Air Zoom Pegasus",
                        "headline": "Run like the wind",
                        "primary_text": "Experience ultimate comfort.",
                        "ad_format": "Video",
                        "platform": "Instagram",
                        "target_audience": "Runners",
                        "objective": "Conversion",
                        "call_to_action": "Shop Now"
                    }
                ],
                "patterns": [
                    {
                        "name": "Dynamic Motion",
                        "description": "Using fast cuts",
                        "effectiveness_score": 8,
                        "platform_suitability": ["Instagram"]
                    }
                ]
            })
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
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
