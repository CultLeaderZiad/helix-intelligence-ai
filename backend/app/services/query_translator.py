"""Translate a Discover query into English or Arabic before scraping.

Ad-library providers match the query string as typed. An Arabic brand name
against an English-indexed library (or the reverse) returns a false empty.
This is a best-effort Groq call: if it fails, the original query is used so
a translation outage cannot block a search.
"""

from __future__ import annotations

import logging
import re

import httpx

from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _looks_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text or ""))


def _looks_latin(text: str) -> bool:
    return bool(_LATIN_RE.search(text or ""))


async def translate_search_query(query: str, target: str) -> str:
    original = (query or "").strip()
    if not original:
        return original
    lang = "ar" if (target or "").lower().startswith("ar") else "en"

    if lang == "en" and not _looks_arabic(original):
        return original
    if lang == "ar" and _looks_arabic(original) and not _looks_latin(original):
        return original

    api_key = env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)
    if not api_key:
        logger.info("Query translation skipped (no GROQ_API_KEY); using original.")
        return original

    language_name = "Arabic" if lang == "ar" else "English"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"Translate the user's ad-library search query into {language_name}. "
                                "Return only the translated query, no quotes or explanation. "
                                "Keep brand names and domains recognizable (e.g. nike.com stays nike.com)."
                            ),
                        },
                        {"role": "user", "content": original},
                    ],
                },
            )
        if response.status_code >= 400:
            logger.warning("Query translation HTTP %s: %s", response.status_code, response.text[:200])
            return original
        text = (
            ((response.json() or {}).get("choices") or [{}])[0]
            .get("message", {})
            .get("content")
            or ""
        ).strip().strip('"').strip("'")
        return text or original
    except Exception as exc:
        logger.warning("Query translation failed: %s", exc)
        return original
