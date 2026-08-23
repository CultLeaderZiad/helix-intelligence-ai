from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    
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
    plan_id: Optional[str] = None

