import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Helix Backend"
    API_V1_STR: str = "/api"

    # SECURITY — must be set via env var; no hardcoded fallback
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    # Versioned Fernet key for BYOK credentials. Never reuse SECRET_KEY.
    CREDENTIAL_ENCRYPTION_KEY: str = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    CREDENTIAL_ENCRYPTION_KEY_PREVIOUS: str = os.getenv("CREDENTIAL_ENCRYPTION_KEY_PREVIOUS", "")
    CREDENTIAL_ENCRYPTION_KEY_VERSION: int = int(os.getenv("CREDENTIAL_ENCRYPTION_KEY_VERSION", "1"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    IMPERSONATION_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("IMPERSONATION_TOKEN_EXPIRE_MINUTES", "15"))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))
    # development | test | staging | production. Unset means development,
    # except a Render process with no explicit class, which is production.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "helix")
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "helix-api")

    # Password reset delivery. The app has no mail provider bundled, so the
    # reset link is logged server-side on every request. Set to true to also
    # return it in the API response (dev/staging convenience only — anyone
    # who can call the endpoint could reset any account).
    # DEFAULTS TO FALSE: must be explicitly opted into. Wire real email
    # delivery (Resend) instead of enabling this in any shared environment.
    AUTH_DEV_RESET_RETURN: bool = os.getenv("AUTH_DEV_RESET_RETURN", "False").lower() in ("true", "1", "yes")

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
    NEON_JWT_ISSUER: str = os.getenv(
        "NEON_JWT_ISSUER",
        os.getenv(
            "NEON_AUTH_BASE_URL",
            "https://ep-fancy-bread-axe99xvb.neonauth.c-4.us-east-2.aws.neon.tech/neondb/auth",
        ),
    )
    NEON_JWT_AUDIENCE: str = os.getenv(
        "NEON_JWT_AUDIENCE",
        os.getenv(
            "NEON_AUTH_BASE_URL",
            "https://ep-fancy-bread-axe99xvb.neonauth.c-4.us-east-2.aws.neon.tech/neondb/auth",
        ),
    )
    NEON_WEBHOOK_SECRET: str = os.getenv("NEON_WEBHOOK_SECRET", "")
    JWKS_REFRESH_LIMIT: int = int(os.getenv("JWKS_REFRESH_LIMIT", "8"))
    JWKS_REFRESH_WINDOW_S: int = int(os.getenv("JWKS_REFRESH_WINDOW_S", "60"))

    # RATE LIMITING (in-memory, per-process token buckets)
    # Protects credential endpoints (brute force / account enumeration) and
    # expensive AI/scrape endpoints (credit burn) from bursts. On a single
    # Render web instance this is sufficient; it is per-process, not global,
    # so limits scale with instance count. Set RATE_LIMIT_ENABLED=false only
    # for local load testing.
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() in ("true", "1", "yes")
    # path-prefix -> (max_requests, window_seconds)
    AUTH_RATE_LIMIT: int = int(os.getenv("AUTH_RATE_LIMIT", "30"))            # per IP per window
    AUTH_RATE_LIMIT_WINDOW_S: int = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_S", "60"))
    EXPENSIVE_RATE_LIMIT: int = int(os.getenv("EXPENSIVE_RATE_LIMIT", "20"))  # per IP per window
    EXPENSIVE_RATE_LIMIT_WINDOW_S: int = int(os.getenv("EXPENSIVE_RATE_LIMIT_WINDOW_S", "60"))
    # Comma-separated IPs or CIDRs of reverse proxies allowed to supply a client IP.
    # Empty means forwarding headers are ignored and the TCP peer is used.
    TRUSTED_PROXY_CIDRS: str = os.getenv("TRUSTED_PROXY_CIDRS", "")


    def __init__(self, **values):
        super().__init__(**values)
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is not set. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        validate_boot_invariants(self)

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
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_TEXT_MODEL: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-flash-latest")
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
    METAPI_API_KEY: str = (

        os.getenv("METAPI_API_KEY", "")
        or os.getenv("METAPI_KEY", "")
        or os.getenv("METAPI_TOKEN", "")
        or os.getenv("Meta_Api", "")
        or os.getenv("META_API", "")
        or os.getenv("meta_api", "")
    ).strip().strip('"\'').strip()
    ADYNTEL_API_KEY: str = os.getenv("ADYNTEL_API_KEY", "")
    ADYNTEL_EMAIL: str = os.getenv("ADYNTEL_EMAIL", "")
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
    # Long jobs are claimed by the worker. Inline dispatch is a local override
    # and is rejected in production.
    HELIX_DISPATCH_INLINE: bool = os.getenv("HELIX_DISPATCH_INLINE", "false").lower() in ("true", "1", "yes")
    WORK_LEASE_S: int = int(os.getenv("WORK_LEASE_S", "120"))
    WORK_MAX_ATTEMPTS: int = int(os.getenv("WORK_MAX_ATTEMPTS", "3"))
    AI_MAX_OUTPUT_TOKENS: int = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1024"))
    AI_CALL_TIMEOUT_S: float = float(os.getenv("AI_CALL_TIMEOUT_S", "20"))
    AI_CALL_DEADLINE_S: float = float(os.getenv("AI_CALL_DEADLINE_S", "45"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "2"))
    MEDIA_GENERATION_DEADLINE_S: float = float(os.getenv("MEDIA_GENERATION_DEADLINE_S", "120"))
    # Managed image/video calls may fall back to Pollinations only when this is set.
    # BYOK failures never use it.
    MEDIA_MANAGED_FALLBACK: bool = os.getenv("MEDIA_MANAGED_FALLBACK", "false").lower() in ("true", "1", "yes")
    SCRAPLING_MIN_INTERVAL_S: float = float(os.getenv("SCRAPLING_MIN_INTERVAL_S", "1.0"))

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

    # SCRAPLING LEAD GENERATION (Scout · Lead Generation sub-product)
    # Worker-gated: when disabled, POST /scout/leadgen/jobs refuses with an
    # honest worker_offline error instead of queueing work nothing will claim.
    SCRAPLING_WORKER_ENABLED: bool = os.getenv("SCRAPLING_WORKER_ENABLED", "False").lower() in ("true", "1", "yes")
    # Dev-only single-process fallback: runs the pipeline as an in-API
    # background task (Scrapling is lazily imported, so uvicorn still boots
    # without browsers). Prefer the Docker worker in production.
    SCRAPLING_INLINE_WORKER: bool = os.getenv("SCRAPLING_INLINE_WORKER", "False").lower() in ("true", "1", "yes")
    SCRAPLING_DEFAULT_ENGINE: str = os.getenv("SCRAPLING_DEFAULT_ENGINE", "stealth")   # http | stealth | dynamic
    SCRAPLING_ROBOTS_OBEY: bool = os.getenv("SCRAPLING_ROBOTS_OBEY", "True").lower() in ("true", "1", "yes")
    SCRAPLING_MAX_CONCURRENCY: int = int(os.getenv("SCRAPLING_MAX_CONCURRENCY", "4"))
    SCRAPLING_PROXY_LIST: str = os.getenv("SCRAPLING_PROXY_LIST", "")   # newline or comma separated proxy URLs
    SCRAPLING_CHECKPOINT_DIR: str = os.getenv("SCRAPLING_CHECKPOINT_DIR", "/tmp/helix-leadgen-checkpoints")
    SCRAPLING_CREDIT_PER_PAGE: float = float(os.getenv("SCRAPLING_CREDIT_PER_PAGE", "0.15"))
    SCRAPLING_CREDIT_BASE: float = float(os.getenv("SCRAPLING_CREDIT_BASE", "1.0"))
    SCRAPLING_DOCKER_IMAGE: str = os.getenv("SCRAPLING_DOCKER_IMAGE", "ghcr.io/d4vinci/scrapling:latest")
    SCRAPLING_WORKER_URL: str = os.getenv("SCRAPLING_WORKER_URL", "")   # optional health ping
    # How recently the worker must have heartbeat before /worker/health says online.
    SCRAPLING_HEARTBEAT_FRESH_S: int = int(os.getenv("SCRAPLING_HEARTBEAT_FRESH_S", "90"))
    # Max log lines persisted on the job (FIFO); UI renders the tail.
    SCRAPLING_MAX_LOG_LINES: int = int(os.getenv("SCRAPLING_MAX_LOG_LINES", "400"))


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


_ENVIRONMENT_ALIASES = {
    "production": "production",
    "prod": "production",
    "staging": "staging",
    "stage": "staging",
    "test": "test",
    "testing": "test",
    "development": "development",
    "dev": "development",
    "local": "development",
    "": "development",
}


def classified_environment(cfg=None) -> str:
    """Return development, test, staging, or production."""
    source = settings if cfg is None else cfg
    raw = (getattr(source, "ENVIRONMENT", "") or "").strip().lower()
    if raw not in _ENVIRONMENT_ALIASES:
        raise RuntimeError(
            f"ENVIRONMENT={raw!r} is not a recognized class. "
            "Use development, test, staging, or production."
        )
    env = _ENVIRONMENT_ALIASES[raw]
    if env == "development" and os.getenv("RENDER"):
        return "production"
    return env


def validate_boot_invariants(cfg) -> None:
    """Refuse to serve when production configuration is unsafe or incomplete."""
    env = classified_environment(cfg)
    if env != "production":
        return
    errors = []
    if getattr(cfg, "USE_MOCKS", False):
        errors.append("USE_MOCKS must be false when ENVIRONMENT=production")
    if getattr(cfg, "HELIX_DISPATCH_INLINE", False):
        errors.append("HELIX_DISPATCH_INLINE must be false when ENVIRONMENT=production")
    if getattr(cfg, "AUTH_DEV_RESET_RETURN", False):
        errors.append("AUTH_DEV_RESET_RETURN must be false when ENVIRONMENT=production")
    secret = getattr(cfg, "SECRET_KEY", "") or ""
    if len(secret) < 32:
        errors.append("Missing or short SECRET_KEY: production requires at least 32 characters")
    encryption_key = (getattr(cfg, "CREDENTIAL_ENCRYPTION_KEY", "") or "").strip()
    if not encryption_key:
        errors.append("Missing required integration key: CREDENTIAL_ENCRYPTION_KEY")
    elif encryption_key == secret:
        errors.append("CREDENTIAL_ENCRYPTION_KEY must not equal SECRET_KEY")
    if not (getattr(cfg, "RESEND_API_KEY", "") or "").strip() or not (getattr(cfg, "RESEND_FROM", "") or "").strip():
        errors.append("Missing required delivery configuration: RESEND_API_KEY and RESEND_FROM")
    app_url = (getattr(cfg, "PUBLIC_APP_BASE_URL", "") or "").strip()
    if not app_url.startswith("https://"):
        errors.append("PUBLIC_APP_BASE_URL must be an https origin in production")
    if getattr(cfg, "APIFY_ENABLED", False) and not (getattr(cfg, "APIFY_API_TOKEN", "") or "").strip():
        errors.append("Missing required integration key: APIFY_API_TOKEN (APIFY_ENABLED is true)")
    for model_name in ("GROQ_MODEL", "GEMINI_TEXT_MODEL", "GEMINI_IMAGE_MODEL"):
        if not (getattr(cfg, model_name, "") or "").strip():
            errors.append(f"Missing required model setting: {model_name}")
    if errors:
        raise RuntimeError("Refusing to serve production traffic: " + "; ".join(errors))


settings = Settings()

# Module-level list used by main.py CORS middleware.
# Import as:  from app.core.config import cors_origins
cors_origins: List[str] = _parse_cors_origins()
