from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SessionResponse(BaseModel):
    user_id: str
    email: str
    role: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    feature_flags: Optional[Dict[str, bool]] = None
    credit_balance: Optional[float] = None
    trial_days_remaining: Optional[int] = None
    plan_id: Optional[str] = None
    has_completed_onboarding: bool = False

