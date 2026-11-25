from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.usage_log import UsageLog
from app.services.ai.base import AIProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.gemini_provider import GeminiProvider


class MultiTierAIProvider(AIProvider):
    """Groq first, Gemini as the fallback. (OpenRouter was removed from the deployment.)"""

    def __init__(self):
        self.groq = GroqProvider()
        self.gemini = GeminiProvider()
        self.model = "groq/openai/gpt-oss-120b"

    async def _call_api(self, messages: List[dict]) -> str:
        errors = {}
        try:
            res = await self.groq._call_api(messages)
            self.model = self.groq.model
            self.last_usage = getattr(self.groq, "last_usage", None)
            return res
        except Exception as e_groq:
            errors["groq"] = str(e_groq)
        try:
            res = await self.gemini._call_api(messages)
            self.model = f"gemini/{self.gemini.model}"
            self.last_usage = getattr(self.gemini, "last_usage", None)
            return res
        except Exception as e_gem:
            errors["gemini"] = str(e_gem)
            raise Exception(f"All AI providers failed: {errors}")


class AIRouter:
    @staticmethod
    async def get_provider_for_user(db: AsyncSession, user: User) -> AIProvider:
            
        # Access, feature flags and credits are enforced before the AI layer
        # (assert_can_spend); there is no separate trial gate here.
        return MultiTierAIProvider()

    @staticmethod
    async def log_usage(db: AsyncSession, user_id: str, provider_name: str, org_id: str, tokens: int = 0):
        log = UsageLog(
            user_id=user_id,
            org_id=org_id,
            provider=provider_name,
            tokens_used=tokens,
            requests_used=1
        )
        db.add(log)
        await db.commit()

    @staticmethod
    async def log_failure(
        db: AsyncSession,
        user_id: str,
        provider_name: str,
        operation: str,
        org_id: str,
        error: str = "",
    ):
        """Records a provider failure so it is visible in the admin
        system-health view. Failure rows never carry credits."""
        log = UsageLog(
            user_id=user_id,
            org_id=org_id,
            provider=provider_name or "unknown",
            operation=operation,
            units=0.0,
            credits_deducted=0.0,
            requests_used=0,
            metadata_json={"status": "failed", "error": (error or "")[:300]},
        )
        db.add(log)
        await db.commit()
