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
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))

    # Deployment environment. Anything that is not an explicit local/dev value
    # is treated as production, so a forgotten env var fails closed.
    ENV: str = os.getenv("ENV", "production").strip().lower()

    # Password reset delivery. The app has no mail provider bundled, so the
    # reset link is logged server-side (which is fine: the logs are ours).
    # Returning it in the API *response* is a dev-only convenience and is a
    # complete account-takeover primitive — POST the email, read the link,
    # own the account — so it is OFF by default and additionally refused
    # unless ENV is a dev value (see allow_reset_link_in_response).
    # render.yaml ships AUTH_DEV_RESET_RETURN=false and Render syncs that on
    # every deploy, so it cannot silently come back after a redeploy.
    AUTH_DEV_RESET_RETURN: bool = os.getenv("AUTH_DEV_RESET_RETURN", "False").lower() in ("true", "1", "yes")

    # Throttles. The per-network buckets are in-process (see core/rate_limit.py
    # for the exact scope caveat); the reset re-issue cooldown is enforced in
    # the database and therefore holds across workers and restarts.
    AUTH_IP_RATE_LIMIT: int = int(os.getenv("AUTH_IP_RATE_LIMIT", "8"))
    AUTH_RATE_WINDOW_SECONDS: int = int(os.getenv("AUTH_RATE_WINDOW_SECONDS", "300"))
    AUTH_RESET_REISSUE_COOLDOWN_SECONDS: int = int(
        os.getenv("AUTH_RESET_REISSUE_COOLDOWN_SECONDS", "120")
    )
    WEBHOOK_RATE_LIMIT: int = int(os.getenv("WEBHOOK_RATE_LIMIT", "60"))
    WEBHOOK_RATE_WINDOW_SECONDS: int = int(os.getenv("WEBHOOK_RATE_WINDOW_SECONDS", "60"))

    @property
    def allow_reset_link_in_response(self) -> bool:
        """True only when the operator asked for it *and* we are not in prod."""
        return bool(self.AUTH_DEV_RESET_RETURN) and self.ENV in ("local", "dev", "development", "test", "pytest")

    # Public app origin used to build password-reset links
    PUBLIC_APP_BASE_URL: str = os.getenv(
        "PUBLIC_APP_BASE_URL",
        "https://helix-intelligence-ai-six.vercel.app",
    ).rstrip("/")

    # CORS — see _parse_cors_origins() below.  Declared as str so
    # pydantic-settings won't try JSON-decoding a comma-separated
    # value from the env var.  main.py imports `cors_origins` (not
    # this field) for the CORS middleware.
    BACKEND_CORS_ORIGINS: str = ""

    # MOCKS
    USE_MOCKS: bool = os.getenv("USE_MOCKS", "False").lower() in ("true", "1")

    # DATABASE
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # NEON AUTH
    NEON_JWKS_URL: str = os.getenv(
        "NEON_JWKS_URL", 
        os.getenv(
            "NEON_AUTH_JWKS_URL",
            "https://ep-fancy-bread-axe99xvb.neonauth.c-4.us-east-2.aws.neon.tech/neondb/auth/.well-known/jwks.json"
        )
    )
    NEON_AUTH_URL: str = os.getenv(
        "NEON_AUTH_BASE_URL",
        "https://ep-fancy-bread-axe99xvb.neonauth.c-4.us-east-2.aws.neon.tech/neondb/auth"
    )
    NEON_WEBHOOK_SECRET: str = os.getenv("NEON_WEBHOOK_SECRET", "")

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
    POLLINATIONS_API_KEY: str = os.getenv("POLLINATIONS_API_KEY", "")
    GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
    SCRAPEGRAPH_API_KEY: str = os.getenv("SCRAPEGRAPH_API_KEY", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    BRIGHTDATA_API_KEY: str = os.getenv("BRIGHTDATA_API_KEY", "")
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "") or os.getenv("APIFY_TOKEN", "")
    APIFY_ENABLED: bool = os.getenv("APIFY_ENABLED", "False").lower() in ("true", "1")
    AIHUBMIX_API_KEY: str = os.getenv("AIHUBMIX_API_KEY", "")
    TOKENHARBOR_API_KEY: str = os.getenv("TOKENHARBOR_API_KEY", "")
    METAPI_API_KEY: str = os.getenv("METAPI_API_KEY", "")
    ADYNTEL_API_KEY: str = os.getenv("ADYNTEL_API_KEY", "")
    ADYNTEL_EMAIL: str = os.getenv("ADYNTEL_EMAIL", "")
    HF_API_KEY_ID: str = os.getenv("HF_API_KEY_ID", "") or os.getenv("HIGGSFIELD_API_KEY_ID", "") or os.getenv("HIGGSFIELD_API_KEY", "")
    HF_API_KEY_SECRET: str = os.getenv("HF_API_KEY_SECRET", "") or os.getenv("HIGGSFIELD_API_KEY_SECRET", "") or os.getenv("HIGGSFIELD_API_SECRET", "") or os.getenv("HIGGSFIELD_SECRET", "")
    HIGGSFIELD_BASE_URL: str = os.getenv("HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai").rstrip("/")
    # Public API origin used to build webhook URLs
    PUBLIC_API_BASE_URL: str = os.getenv(
        "PUBLIC_API_BASE_URL",
        "https://helix-intelligence-ai.onrender.com/api",
    ).rstrip("/")

    # 7-DAY TRIAL & MEDIA GENERATION LIMITS
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "7"))
    TRIAL_IMAGES_PER_DAY: int = int(os.getenv("TRIAL_IMAGES_PER_DAY", "5"))
    TRIAL_IMAGES_TOTAL: int = int(os.getenv("TRIAL_IMAGES_TOTAL", "25"))
    PAID_IMAGES_PER_DAY: int = int(os.getenv("PAID_IMAGES_PER_DAY", "50"))

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
        origins = json.loads(raw)
        return [o.rstrip("/") for o in origins]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


settings = Settings()

# Module-level list used by main.py CORS middleware.
# Import as:  from app.core.config import cors_origins
cors_origins: List[str] = _parse_cors_origins()
