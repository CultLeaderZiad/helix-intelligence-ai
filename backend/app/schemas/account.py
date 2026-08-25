from pydantic import BaseModel
from typing import Optional

class TrialStatusResponse(BaseModel):
    active: bool
    days_remaining: int
    requests_used: int
    requests_limit: int
    daily_credit_limit: Optional[float] = None
    daily_credits_used: Optional[float] = None
    daily_credits_remaining: Optional[float] = None
    daily_credits_resets_at_utc: Optional[str] = None
