"""Optional Sentry error reporting. Off unless SENTRY_DSN is set.

Free-tier friendly: errors only (no tracing or profiling unless
SENTRY_TRACES_SAMPLE_RATE is raised), no default PII, and every event is
scrubbed before it leaves the process: auth headers, cookies, secrets and
email addresses never reach Sentry.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SENSITIVE_KEYS = (
    "authorization", "cookie", "set-cookie", "x-admin-secret", "x-cron-secret",
    "x-helix-edge-secret", "password", "token", "secret", "api_key", "apikey",
    "access_token", "refresh_token", "email",
)
FILTERED = "[Filtered]"
# Secret-bearing query parameters (reset/invite links carry ?token=...). Masked
# wherever they appear in a string: request.url, query_string, breadcrumbs.
SECRET_PARAM_RE = re.compile(
    r"(?i)(^|[?&;\s])(token|access_token|refresh_token|code|secret|password|api_key|apikey|key|signature|sig)=([^&#\s;\"']+)"
)


def _sensitive(key: Any) -> bool:
    k = str(key).lower()
    return any(s in k for s in SENSITIVE_KEYS)


def scrub(value: Any) -> Any:
    """Recursively drop secrets and mask email addresses."""
    if isinstance(value, dict):
        return {k: (FILTERED if _sensitive(k) else scrub(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(scrub(v) for v in value)
    if isinstance(value, str):
        return SECRET_PARAM_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}={FILTERED}", EMAIL_RE.sub("[email]", value))
    return value


def before_send(event: dict, _hint: dict | None = None) -> dict:
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("cookies", None)
        request.pop("data", None)  # request bodies can hold passwords and emails
        if isinstance(request.get("headers"), dict):
            request["headers"] = {
                k: (FILTERED if _sensitive(k) else v) for k, v in request["headers"].items()
            }
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if user.get("id") else {}
    return scrub(event)


def init_error_reporting() -> bool:
    """Start Sentry when SENTRY_DSN is set. Returns True when started."""
    dsn = (getattr(settings, "SENTRY_DSN", "") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; error reporting is off")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=str(getattr(settings, "ENVIRONMENT", "") or "production"),
        send_default_pii=False,
        traces_sample_rate=float(getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.0) or 0.0),
        max_request_body_size="never",
        before_send=before_send,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )
    logger.info("Sentry error reporting is on")
    return True
