import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.user import User
from app.models.usage_log import UsageLog
from app.services.ai.base import AIProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.openrouter_provider import OpenRouterProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.byok_provider import BYOKProvider
from app.services.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.core.config import settings

TRIAL_DAILY_REQUEST_LIMIT = 20

class MultiTierAIProvider(AIProvider):
    def __init__(self):
        self.groq = GroqProvider()
        self.openrouter = OpenRouterProvider(trial_mode=True)
        self.gemini = GeminiProvider()
        self.aihubmix = OpenAICompatibleProvider(
            base_url="https://aihubmix.com/v1",
            api_key=settings.AIHUBMIX_API_KEY,
            default_model="glm-4.7-flash-free"
        ) if settings.AIHUBMIX_API_KEY else None
        self.tokenharbor = OpenAICompatibleProvider(
            base_url="https://tokenharbor.ai/v1",
            api_key=settings.TOKENHARBOR_API_KEY,
            default_model="qwen3.8-27b:free"
        ) if settings.TOKENHARBOR_API_KEY else None
        self.model = "groq/openai/gpt-oss-120b"
        
    async def _call_api(self, messages: List[dict]) -> str:
        errors = {}
        # Tier 1: Groq (Primary)
        try:
            res = await self.groq._call_api(messages)
            self.model = "groq/openai/gpt-oss-120b"
            return res
        except Exception as e_groq:
            errors["groq"] = str(e_groq)
            
            # Tier 2: OpenRouter (Fallback)
            try:
                res = await self.openrouter._call_api(messages)
                self.model = f"openrouter/{self.openrouter.model}"
                return res
            except Exception as e_or:
                errors["openrouter"] = str(e_or)
                
                # Tier 3: AIHubMix (Tertiary Fallback)
                if self.aihubmix:
                    try:
                        res = await self.aihubmix._call_api(messages)
                        self.model = f"aihubmix/{self.aihubmix.model}"
                        return res
                    except Exception as e_ah:
                        errors["aihubmix"] = str(e_ah)
                else:
                    errors["aihubmix"] = "skipped (no API key)"
                    
                # Tier 4: Token Harbor (Quaternary Fallback)
                if self.tokenharbor:
                    try:
                        res = await self.tokenharbor._call_api(messages)
                        self.model = f"tokenharbor/{self.tokenharbor.model}"
                        return res
                    except Exception as e_th:
                        errors["tokenharbor"] = str(e_th)
                else:
                    errors["tokenharbor"] = "skipped (no API key)"
                    
                # Tier 5: Gemini (Final Fallback)
                try:
                    res = await self.gemini._call_api(messages)
                    self.model = f"gemini/{self.gemini.model}"
                    return res
                except Exception as e_gem:
                    errors["gemini"] = str(e_gem)
                    raise Exception(f"All AI providers failed: {errors}")

class AIRouter:
    @staticmethod
    async def get_provider_for_user(db: AsyncSession, user: User, byok_key: str = None, byok_provider: str = None) -> AIProvider:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Check if BYOK is provided
        if byok_key and byok_provider:
            return BYOKProvider(api_key=byok_key, provider_choice=byok_provider)
            
        # 2. Check Trial Status
        if user.trial_expires_at and now > user.trial_expires_at:
            raise HTTPException(
                status_code=403, 
                detail={
                    "error": "trial_expired", 
                    "message": "Your 7-day free trial has expired. Please upgrade your plan or provide your own API key."
                }
            )
            
        # Enforce Trial Limits
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user.id,
            UsageLog.created_at >= today_start
        )
        usage_count = await db.scalar(query)
        if usage_count >= TRIAL_DAILY_REQUEST_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "trial_limit_reached",
                    "message": f"You have reached the daily limit of {TRIAL_DAILY_REQUEST_LIMIT} requests during your trial."
                }
            )
            
        # Return resilient multi-tier provider (Groq -> OpenRouter -> Gemini)
        return MultiTierAIProvider()

    @staticmethod
    async def log_usage(db: AsyncSession, user_id: str, provider_name: str, org_id: str = None, tokens: int = 0):
        log = UsageLog(
            user_id=user_id,
            org_id=org_id,
            provider=provider_name,
            tokens_used=tokens,
            requests_used=1
        )
        db.add(log)
        await db.commit()
