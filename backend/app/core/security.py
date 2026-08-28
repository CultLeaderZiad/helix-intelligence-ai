from datetime import datetime, timedelta, timezone
import asyncio
import bcrypt
from jose import jwt, JWTError
from app.core.config import settings

ALGORITHM = "HS256"

def verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Synchronous bcrypt verify — blocks for ~300ms. Use async wrapper below."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash_sync(password: str) -> str:
    """Synchronous bcrypt hash — blocks for ~300ms. Use async wrapper below."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Run bcrypt verify in a thread so it doesn't block the event loop."""
    return await asyncio.to_thread(verify_password_sync, plain_password, hashed_password)

async def get_password_hash(password: str) -> str:
    """Run bcrypt hash in a thread so it doesn't block the event loop."""
    return await asyncio.to_thread(get_password_hash_sync, password)

def create_access_token(subject: str, role: str, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
