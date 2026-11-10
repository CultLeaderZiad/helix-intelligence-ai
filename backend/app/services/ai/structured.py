"""Reject incomplete model output before it is stored or charged."""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from app.schemas.analysis import Pattern

_INSIGHT_KINDS = {"opportunity", "warning", "observation"}
_PATTERN_FAMILIES = {"visual", "copy", "structural"}
_ENTITY_TYPES = {
    "creator_streamer",
    "ecommerce_brand",
    "saas_tech",
    "public_figure",
    "general",
}


class InvalidModelOutput(ValueError):
    """The provider returned JSON that does not satisfy the contract."""


def _require_text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidModelOutput(f"missing {key}")
    return value.strip()


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidModelOutput("confidence is not a number") from exc
    if number < 0 or number > 1:
        raise InvalidModelOutput("confidence is outside 0..1")
    return number




def parse_patterns(data: Any, *, allowed_ids: Iterable[str], model_version: str) -> list:
    allowed = set(allowed_ids)
    if isinstance(data, dict):
        items = data.get("patterns")
    elif isinstance(data, list):
        items = data
    else:
        raise InvalidModelOutput("pattern response is not an object")
    if not isinstance(items, list) or not items:
        raise InvalidModelOutput("patterns are missing")
    parsed = []
    total = len(allowed) or 1
    for item in items:
        if not isinstance(item, dict):
            raise InvalidModelOutput("pattern entry is not an object")
        family = _require_text(item, "family")
        if family not in _PATTERN_FAMILIES:
            raise InvalidModelOutput("pattern family is not allowed")
        evidence = item.get("evidence_creative_ids")
        if not isinstance(evidence, list) or not evidence:
            raise InvalidModelOutput("pattern evidence_creative_ids is missing")
        if any(not isinstance(eid, str) or eid not in allowed for eid in evidence):
            raise InvalidModelOutput("pattern evidence id is not in the supplied creatives")
        prevalence = len(set(evidence)) / total
        parsed.append(Pattern(
            id=f"pattern_{uuid.uuid4().hex}",
            label=_require_text(item, "label"),
            family=family,
            prevalence=prevalence,
            lift_index=None,
            model_version=model_version,
            evidence_creative_ids=list(dict.fromkeys(evidence)),
        ))
    return parsed






def parse_entity(data: Any) -> dict:
    if not isinstance(data, dict):
        raise InvalidModelOutput("entity response is not an object")
    entity_type = _require_text(data, "entity_type")
    if entity_type not in _ENTITY_TYPES:
        raise InvalidModelOutput("entity_type is not allowed")
    summary = _require_text(data, "summary")
    return {
        "entity_name": _require_text(data, "entity_name"),
        "entity_type": entity_type,
        "category_label": data.get("category_label") if isinstance(data.get("category_label"), str) else entity_type,
        "summary": summary,
        "runs_direct_meta_ads": bool(data.get("runs_direct_meta_ads")) if isinstance(data.get("runs_direct_meta_ads"), bool) else None,
        "disambiguation": data.get("disambiguation") if isinstance(data.get("disambiguation"), dict) else {},
        "playbook_and_takeaways": data.get("playbook_and_takeaways") if isinstance(data.get("playbook_and_takeaways"), list) else [],
        "evidence_status": "model_hypothesis",
        "evidence_label": "Unverified model hypothesis. Not fetched from the ad library.",
        "social_links": {},
    }


def parse_outreach(data: Any) -> dict:
    if not isinstance(data, dict):
        raise InvalidModelOutput("outreach response is not an object")
    return {
        "subject": _require_text(data, "subject")[:200],
        "body": _require_text(data, "body")[:2000],
        "dm": (data.get("dm") if isinstance(data.get("dm"), str) else "")[:500],
        "personalization_points": [str(x) for x in (data.get("personalization_points") or [])[:6] if str(x).strip()],
        "sent": False,
    }


