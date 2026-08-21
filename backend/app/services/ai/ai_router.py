import datetime
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

TRIAL_DAILY_REQUEST_LIMIT = 20

class AIRouter:
    @staticmethod
    async def get_provider_for_user(db: AsyncSession, user: User, byok_key: str = None, byok_provider: str = None) -> AIProvider:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Check if BYOK is provided
        if byok_key and byok_provider:
            return BYOKProvider(api_key=byok_key, provider_choice=byok_provider)
            
        # 2. Check if user has an active paid plan (stubbed logic for future)
        # if user.organization and user.organization.plan != "free":
        #    return PaidProvider()
            
        # 3. Check Trial Status
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
            
        # Route to free tier provider
        # We can implement load balancing or fallback logic here.
        # Defaulting to Groq for fast inference
        try:
            return GroqProvider()
        except Exception:
            try:
                return OpenRouterProvider(trial_mode=True)
            except Exception:
                return GeminiProvider()

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
