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

    # Password reset delivery. The app has no mail provider bundled, so the
    # reset link is logged server-side on every request. Set to true to also
    # return it in the API response (dev/staging convenience only — anyone
    # who can call the endpoint could reset any account). Disable as soon as
    # real email delivery is wired up.
    AUTH_DEV_RESET_RETURN: bool = os.getenv("AUTH_DEV_RESET_RETURN", "True").lower() in ("true", "1", "yes")

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
    # Empty APIFY_ENABLED means "on if a token is present". Set false/0 to force off.
    APIFY_ENABLED: bool = (
        os.getenv("APIFY_ENABLED", "").lower() in ("true", "1", "yes")
        if os.getenv("APIFY_ENABLED", "").strip()
        else bool((os.getenv("APIFY_API_TOKEN", "") or os.getenv("APIFY_TOKEN", "")).strip())
    )
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

    # OBJECT STORAGE (Cloudflare R2, S3-compatible)
    # Render's disk is ephemeral: anything written locally is destroyed on the
    # next restart or deploy. When these are set, generated media is written to
    # R2 instead and survives. When they are not set, storage falls back to the
    # local disk so local development keeps working.
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "")
    # Public read origin for the bucket (r2.dev subdomain or a custom domain).
    # Required: without it we would have to hand out presigned URLs, which
    # expire (7 days max) and would silently rot in the database.
    R2_PUBLIC_BASE_URL: str = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")
    # Optional override; normally derived from the account id.
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "").rstrip("/")

    # JOB RESILIENCE
    # A live job writes a heartbeat every JOB_HEARTBEAT_INTERVAL_S seconds.
    # On boot, an active job owned by a previous process that has been silent
    # for longer than JOB_STALE_AFTER_S is treated as dead. This is silence,
    # not total runtime, so a legitimately slow search is never swept.
    JOB_HEARTBEAT_INTERVAL_S: int = int(os.getenv("JOB_HEARTBEAT_INTERVAL_S", "15"))
    JOB_STALE_AFTER_S: int = int(os.getenv("JOB_STALE_AFTER_S", "120"))

    # MONITORS (scheduled competitor watches)
    # The scheduler is whatever calls POST /api/monitors/tick with this secret
    # in the X-Cron-Secret header: a Render Cron Job, or any external cron.
    # When unset the tick endpoint refuses every request, so an unconfigured
    # deployment is closed rather than open.
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")
    # A tick dispatches at most this many monitors, so a backlog cannot bury
    # the single web instance under concurrent scrapes.
    MONITOR_MAX_PER_TICK: int = int(os.getenv("MONITOR_MAX_PER_TICK", "3"))
    # Consecutive absences before an ad is reported killed. See
    # creative_fingerprint: one absence is usually a flaky scrape.
    MONITOR_MISS_THRESHOLD: int = int(os.getenv("MONITOR_MISS_THRESHOLD", "2"))
    # Consecutive failed runs before a monitor pauses itself, so a permanently
    # broken query stops burning credits.
    MONITOR_MAX_FAILURES: int = int(os.getenv("MONITOR_MAX_FAILURES", "5"))
    # How long a monitor run may take before the reconciler treats it as dead.
    MONITOR_RUN_TIMEOUT_S: int = int(os.getenv("MONITOR_RUN_TIMEOUT_S", "900"))

    # EMAIL (Resend). Unset means email fan-out is skipped and only in-app
    # notifications are delivered; it is never a hard failure.
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM: str = os.getenv("RESEND_FROM", "")
    # Origin used to build links in emails and notifications.
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:5173").rstrip("/")

    # 7-DAY TRIAL & MEDIA GENERATION LIMITS
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "7"))
    TRIAL_IMAGES_PER_DAY: int = int(os.getenv("TRIAL_IMAGES_PER_DAY", "5"))
    TRIAL_IMAGES_TOTAL: int = int(os.getenv("TRIAL_IMAGES_TOTAL", "25"))
    PAID_IMAGES_PER_DAY: int = int(os.getenv("PAID_IMAGES_PER_DAY", "50"))

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=("../.env", "../.env.local", ".env", ".env.local"),
        extra="ignore",
        env_ignore_empty=True,
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
