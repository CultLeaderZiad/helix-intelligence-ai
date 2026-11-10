"""Transactional email via Resend.

Helix talks to the REST API from FastAPI (httpx), not the Node ``resend``
SDK. The two calls monitors need:

* ``POST /emails`` — ``emails.send``
* ``GET /emails/{id}`` — ``emails.get`` (needs a full-access key; a
  sending-only key accepts the send and then returns ``restricted_api_key``)

Batch, update, cancel, share, attachments and metrics are unused.

Credential-driven in the same way as object storage: with no API key the
service reports itself disabled and every send becomes a logged no-op. A
monitor run must never fail because email is unconfigured — the in-app
notification is the primary channel and email is an addition to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Optional
import logging

import httpx

from app.core.config import DEFAULT_SUPPORT_EMAIL, settings

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


@dataclass
class SendResult:
    accepted: bool
    email_id: Optional[str] = None
    last_event: Optional[str] = None
    error: Optional[str] = None

    def __bool__(self) -> bool:
        return self.accepted


def email_enabled() -> bool:
    if settings.RESEND_API_KEY and settings.RESEND_FROM:
        return True
    if settings.RESEND_API_KEY or settings.RESEND_FROM:
        logger.error(
            "Email is partially configured and therefore disabled. "
            "Both RESEND_API_KEY and RESEND_FROM are required."
        )
    return False


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}


def support_address() -> str:
    """Reply-To and the address printed in every transactional footer."""
    value = (getattr(settings, "SUPPORT_EMAIL", "") or "").strip()
    return value or DEFAULT_SUPPORT_EMAIL


def append_support_footer(html: str, text: Optional[str]) -> tuple[str, Optional[str]]:
    """Add the support address once, as the message footer."""
    address = support_address()
    safe = escape(address, quote=True)
    marker = f"mailto:{safe}"
    if marker not in (html or ""):
        html = (
            f"{html}\n"
            f'<p style="margin-top:28px;font-size:12px;color:#666;">'
            f'Questions? Reply to this email or write to '
            f'<a href="{marker}">{safe}</a>.</p>'
        )
    if text and address not in text:
        text = text.rstrip() + f"\n\nQuestions? Reply to this email or write to {address}."
    return html, text


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> SendResult:
    """Returns whether the message was accepted by Resend, plus the email id.

    Never raises: callers are background jobs where a bounced digest must not
    take down the run that produced it. The id is what lets a later retrieve
    prove delivery (`last_event`) instead of just "the POST returned 200".
    """
    if not email_enabled():
        logger.info("Email skipped (Resend not configured): %s -> %s", subject, to)
        return SendResult(False, error="not_configured")
    if not to:
        return SendResult(False, error="missing_recipient")

    html, text = append_support_footer(html, text)
    payload = {
        "from": settings.RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
        "reply_to": support_address(),
    }
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                RESEND_ENDPOINT,
                json=payload,
                headers=_headers(),
            )
        if response.status_code >= 400:
            logger.error(
                "Resend rejected message to %s (%s): %s",
                to, response.status_code, response.text[:400],
            )
            return SendResult(False, error=f"http_{response.status_code}")
        email_id = (response.json() or {}).get("id")
        return SendResult(True, email_id=email_id)
    except Exception as exc:
        logger.error("Email send to %s failed: %s", to, exc)
        return SendResult(False, error=str(exc))


async def retrieve_email(email_id: str) -> Optional[dict]:
    """GET /emails/{id}. Used to read `last_event` after a send."""
    if not email_enabled() or not email_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{RESEND_ENDPOINT}/{email_id}",
                headers=_headers(),
            )
        if response.status_code >= 400:
            logger.error(
                "Resend retrieve %s failed (%s): %s",
                email_id, response.status_code, response.text[:200],
            )
            return None
        return response.json()
    except Exception as exc:
        logger.error("Resend retrieve %s failed: %s", email_id, exc)
        return None
