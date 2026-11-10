"""Search-time filters sent to the ad library (Metapi), validated once.

Result-view filters (``min_days_active``, ``min_score``) are applied to stored
results and pass through untouched. Search-time filters are checked here so
an invalid value is a 422, not a provider error that still costs records.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, Optional

ACTIVE_STATUSES = ("active", "inactive", "all")
MEDIA_TYPES = ("all", "image", "video", "meme")
PLATFORMS = ("facebook", "instagram", "messenger", "audience_network", "whatsapp")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_LANGUAGE = re.compile(r"^[a-z]{2}$")
MAX_LANGUAGES = 5

SEARCH_KEYS = (
    "country", "active_status", "media_type", "start_date_min", "start_date_max",
    "publisher_platforms", "content_languages",
)


def _date(value: Any, name: str) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be a date (YYYY-MM-DD)") from exc


def _list(value: Any) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected a list")
    return [str(v).strip().lower() for v in value if str(v).strip()]


def normalize_search_filters(filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the filters with search-time keys validated and normalized.

    Raises ValueError with a user-safe message on an invalid value.
    """
    out = dict(filters or {})
    country = str(out.get("country") or "ALL").strip().upper()
    if country != "ALL" and not _COUNTRY.match(country):
        raise ValueError("country must be a two-letter code or ALL")
    out["country"] = country

    for key, allowed in (("active_status", ACTIVE_STATUSES), ("media_type", MEDIA_TYPES)):
        value = out.get(key)
        if value in (None, ""):
            out.pop(key, None)
            continue
        value = str(value).strip().lower()
        if value not in allowed:
            raise ValueError(f"{key} must be one of {', '.join(allowed)}")
        out[key] = value

    start_min = _date(out.get("start_date_min"), "start_date_min")
    start_max = _date(out.get("start_date_max"), "start_date_max")
    if start_min and start_max and start_min > start_max:
        raise ValueError("start_date_min must not be after start_date_max")
    for key, value in (("start_date_min", start_min), ("start_date_max", start_max)):
        if value:
            out[key] = value
        else:
            out.pop(key, None)

    platforms = sorted(set(_list(out.get("publisher_platforms"))))
    if any(p not in PLATFORMS for p in platforms):
        raise ValueError(f"publisher_platforms must be from {', '.join(PLATFORMS)}")
    languages = sorted(set(_list(out.get("content_languages"))))
    if any(not _LANGUAGE.match(code) for code in languages) or len(languages) > MAX_LANGUAGES:
        raise ValueError(f"content_languages must be up to {MAX_LANGUAGES} two-letter codes")
    for key, value in (("publisher_platforms", platforms), ("content_languages", languages)):
        if value:
            out[key] = value
        else:
            out.pop(key, None)
    return out


def metapi_task_filters(filters: Optional[Dict[str, Any]], *, advertiser: bool) -> Dict[str, Any]:
    """Metapi task fields for the search-time filters (docs: POST /v1/tasks).

    Keyword tasks always need a country (ALL allowed). Advertiser tasks
    default to all countries and all statuses, so only explicit choices go.
    """
    f = normalize_search_filters(filters)
    payload: Dict[str, Any] = {}
    if f["country"] != "ALL" or not advertiser:
        payload["country"] = f["country"]
    for key in ("active_status", "media_type", "publisher_platforms", "content_languages"):
        if key in f and not (key == "media_type" and f[key] == "all"):
            payload[key] = f[key]
    if "start_date_min" in f:
        payload["start_date[min]"] = f["start_date_min"]
    if "start_date_max" in f:
        payload["start_date[max]"] = f["start_date_max"]
    return payload
