"""Translate a Discover query into English or Arabic before scraping.

Ad-library providers match the query string as typed. An Arabic brand name
against an English-indexed library (or the reverse) returns a false empty.
This is a best-effort Groq call: if it fails, the original query is used so
a translation outage cannot block a search.
"""

from __future__ import annotations

import logging
import re

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

    result = await translate_search_query_result(original, target)
    return result.text


async def translate_search_query_result(query: str, target: str):
    """Return the original query when the provider is unavailable. Never invent a translation."""
    from app.services.ai.call_policy import complete_chat
    from app.services.ai.prompts import PROMPT_QUERY, query_messages

    original = (query or "").strip()
    lang = "ar" if (target or "").lower().startswith("ar") else "en"

    class _QueryResult:
        def __init__(self, text, status, model="", prompt_version=PROMPT_QUERY):
            self.text = text
            self.status = status
            self.model = model
            self.prompt_version = prompt_version

    if not original:
        return _QueryResult(original, "empty")
    if lang == "en" and not _looks_arabic(original):
        return _QueryResult(original, "not_needed")
    if lang == "ar" and _looks_arabic(original) and not _looks_latin(original):
        return _QueryResult(original, "not_needed")

    api_key = env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)
    if not api_key:
        logger.info("Query translation skipped (no GROQ_API_KEY); using original.")
        return _QueryResult(original, "unavailable")

    language_name = "Arabic" if lang == "ar" else "English"
    try:
        result = await complete_chat(
            provider_name="groq",
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=api_key,
            model="llama-3.1-8b-instant",
            messages=query_messages(original, language_name),
            allowed_hosts={"api.groq.com"},
            response_format=None,
            max_retries=0,
        )
        text = (result.text or "").strip().strip('"').strip("'")
        if not text:
            return _QueryResult(original, "unavailable")
        return _QueryResult(text, "ok", model=result.model)
    except Exception as exc:
        logger.warning("Query translation failed: %s", exc)
        return _QueryResult(original, "unavailable")
