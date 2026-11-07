"""Customer lifecycle email: the welcome message sent after sign-up.

Best-effort only: email is never a hard failure (see email_service) and every
send is guarded by ``email_enabled()``. Access is granted by a platform admin,
so the welcome message explains that instead of promising credits or a trial.
"""

from __future__ import annotations

import logging


from app.core.config import settings
from app.models.user import User
from app.services.email_service import send_email, email_enabled

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return (settings.APP_BASE_URL or "http://localhost:5173").rstrip("/")


def _wrap(title: str, body_html: str, cta_label: str, cta_path: str) -> str:
    """Minimal branded HTML shell. Inline styles only (email clients strip <style>)."""
    url = f"{_base_url()}{cta_path}"
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#0A0A0A;color:#EDEDED;padding:32px;">
      <div style="max-width:560px;margin:0 auto;background:#111;border:1px solid #222;border-radius:12px;padding:32px;">
        <div style="font-size:13px;letter-spacing:2px;color:#6366F1;font-weight:700;margin-bottom:16px;">HELIX INTELLIGENCE</div>
        <h1 style="font-size:22px;margin:0 0 16px;color:#fff;">{title}</h1>
        <div style="font-size:15px;line-height:1.6;color:#B5B5B5;">{body_html}</div>
        <a href="{url}" style="display:inline-block;margin-top:24px;background:#6366F1;color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;">{cta_label}</a>
        <p style="margin-top:28px;font-size:12px;color:#666;">You received this because you created a Helix Intelligence account.</p>
      </div>
    </div>
    """


async def send_welcome_email(email_or_user: User | str, name: str = "") -> None:
    if not email_enabled():
        return
    if isinstance(email_or_user, str):
        target_email = email_or_user.strip()
        clean_name = (name or target_email.split("@")[0]).strip() or "there"
    else:
        target_email = getattr(email_or_user, "email", "")
        clean_name = (getattr(email_or_user, "full_name", None) or target_email.split("@")[0]).strip() or "there"

    if not target_email:
        return

    html = _wrap(
        f"Welcome to Helix, {clean_name}",
        "Your account is created. A Helix administrator grants workspace access; "
        "you can request it from the Access page, and you will see the status there.",
        "Request access",
        "/access",
    )
    result = await send_email(to=target_email, subject="Welcome to Helix Intelligence", html=html)
    logger.info("Welcome email: %s", "sent" if result else getattr(result, "error", "failed"))
