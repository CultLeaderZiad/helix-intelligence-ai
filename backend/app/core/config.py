import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Helix Backend"
    API_V1_STR: str = "/api"

    # SECURITY — must be set via env var; no hardcoded fallback
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # CORS — see _parse_cors_origins() below.  Declared as str so
    # pydantic-settings won't try JSON-decoding a comma-separated
    # value from the env var.  main.py imports `cors_origins` (not
    # this field) for the CORS middleware.
    BACKEND_CORS_ORIGINS: str = ""

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
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Please check your .env or .env.local file."
            )
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        for bad in ("channel_binding=require&", "&channel_binding=require", "?channel_binding=require"):
            url = url.replace(bad, "" if "&" in bad else "?" if "?" in bad else "")
        return url

    # API KEYS
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SCRAPEGRAPH_API_KEY: str = os.getenv("SCRAPEGRAPH_API_KEY", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    BRIGHTDATA_API_KEY: str = os.getenv("BRIGHTDATA_API_KEY", "")
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "") or os.getenv("APIFY_TOKEN", "")
    AIHUBMIX_API_KEY: str = os.getenv("AIHUBMIX_API_KEY", "")
    TOKENHARBOR_API_KEY: str = os.getenv("TOKENHARBOR_API_KEY", "")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=("../.env", "../.env.local", ".env", ".env.local"),
        extra="ignore",
    )


# ---------------------------------------------------------------------------
# CORS origins — parsed from env var, NOT from pydantic fields, because
# pydantic-settings tries to JSON-decode List[str] env vars which breaks
# comma-separated values.  This is the single source of truth for CORS
# origins throughout the app.
# ---------------------------------------------------------------------------
def _parse_cors_origins() -> List[str]:
    """Parse BACKEND_CORS_ORIGINS env var.

    Accepts comma-separated:
        "https://app.vercel.app,https://preview.vercel.app"
    or JSON array:
        '["https://app.vercel.app"]'

    Returns localhost defaults when the var is unset/empty.
    """
    raw = os.getenv("BACKEND_CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173", "http://localhost:3000"]
    if raw.startswith("["):
        return json.loads(raw)
    return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()

# Module-level list used by main.py CORS middleware.
# Import as:  from app.core.config import cors_origins
cors_origins: List[str] = _parse_cors_origins()
