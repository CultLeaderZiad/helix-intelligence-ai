import httpx
from typing import List
from app.services.ai.base import AIProvider

class BYOKProvider(AIProvider):
    def __init__(self, api_key: str, provider_choice: str = "openai", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.provider_choice = provider_choice
        self.model = model
        
    async def _call_api(self, messages: List[dict]) -> str:
        if self.provider_choice == "openai":
            base_url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1000
            }
        elif self.provider_choice == "anthropic":
            base_url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            # Extract system message for Anthropic API
            system_msg = ""
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg += msg["content"] + "\n"
                else:
                    filtered_messages.append(msg)
                    
            payload = {
                "model": self.model,
                "messages": filtered_messages,
                "system": system_msg,
                "temperature": 0.3,
                "max_tokens": 1000
            }
        else:
            raise Exception(f"Unsupported BYOK provider: {self.provider_choice}")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if self.provider_choice == "openai":
                return data["choices"][0]["message"]["content"]
            elif self.provider_choice == "anthropic":
                return data["content"][0]["text"]
