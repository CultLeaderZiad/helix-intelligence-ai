import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Helix Backend"
    API_V1_STR: str = "/api"
    
    # SECURITY — must be set via env var; no hardcoded fallback
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ]
    
    # MOCKS
    USE_MOCKS: bool = os.getenv("USE_MOCKS", "True").lower() in ("true", "1")

    # DATABASE
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is not set. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if not url:
            raise ValueError("DATABASE_URL environment variable is not set. Please check your .env or .env.local file.")
        
        # Ensure asyncpg dialect
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            
        # Fix sslmode and other params for asyncpg
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        if "channel_binding=require&" in url:
            url = url.replace("channel_binding=require&", "")
        if "&channel_binding=require" in url:
            url = url.replace("&channel_binding=require", "")
        if "?channel_binding=require" in url:
            url = url.replace("?channel_binding=require", "?")
            
        return url

    # API KEYS
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SCRAPEGRAPH_API_KEY: str = os.getenv("SCRAPEGRAPH_API_KEY", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    BRIGHTDATA_API_KEY: str = os.getenv("BRIGHTDATA_API_KEY", "")
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "") or os.getenv("APIFY_TOKEN", "")

    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file=("../.env", "../.env.local", ".env", ".env.local"), 
        extra="ignore"
    )

settings = Settings()
