"""Reject incomplete model output before it is stored or charged."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Iterable

from app.schemas.analysis import Insight, Pattern
from app.schemas.simulation import SegmentReaction

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


def parse_insight(data: Any, *, creative_id: str, model_version: str) -> Insight:
    if not isinstance(data, dict):
        raise InvalidModelOutput("insight response is not an object")
    kind = _require_text(data, "kind")
    if kind not in _INSIGHT_KINDS:
        raise InvalidModelOutput("kind is not an allowed value")
    evidence = data.get("evidence_creative_ids")
    if not isinstance(evidence, list) or creative_id not in evidence:
        raise InvalidModelOutput("evidence_creative_ids must include the creative")
    if any(item != creative_id for item in evidence):
        raise InvalidModelOutput("evidence_creative_ids contains an unknown id")
    return Insight(
        id=f"insight_{uuid.uuid4().hex}",
        creative_id=creative_id,
        kind=kind,
        title=_require_text(data, "title"),
        summary=_require_text(data, "summary"),
        confidence=_confidence(data.get("confidence")),
        evidence_creative_ids=[creative_id],
        model_version=model_version,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        emotional_resonance=data.get("emotional_resonance") if isinstance(data.get("emotional_resonance"), str) else None,
        script_teardown=data.get("script_teardown") if isinstance(data.get("script_teardown"), str) else None,
        fatigue_prediction=data.get("fatigue_prediction") if isinstance(data.get("fatigue_prediction"), str) else None,
    )


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


def parse_simulation(data: Any, segments) -> dict:
    if not isinstance(data, dict):
        raise InvalidModelOutput("simulation response is not an object")
    raw = data.get("segment_reactions")
    if not isinstance(raw, list) or not raw:
        raise InvalidModelOutput("segment_reactions is missing")
    by_id = {segment.id: segment for segment in segments}
    reactions = []
    for item in raw:
        if not isinstance(item, dict):
            raise InvalidModelOutput("segment reaction is not an object")
        segment = by_id.get(item.get("segment_id"))
        if segment is None:
            raise InvalidModelOutput("segment_id is not one of the requested personas")
        try:
            appeal = float(item.get("appeal_score"))
        except (TypeError, ValueError) as exc:
            raise InvalidModelOutput("appeal_score is not a number") from exc
        if appeal < 0 or appeal > 1:
            raise InvalidModelOutput("appeal_score is outside 0..1")
        credibility = item.get("credibility_assessment")
        if not isinstance(credibility, str) or not credibility.strip():
            raise InvalidModelOutput("credibility_assessment is missing")
        reactions.append(SegmentReaction(
            segment_id=segment.id,
            segment_label=segment.label,
            appeal_score=appeal,
            objections=[str(x) for x in item.get("objections") or [] if str(x).strip()],
            confusing_claims=[str(x) for x in item.get("confusing_claims") or [] if str(x).strip()],
            credibility_assessment=credibility.strip(),
            compliance_risks=[str(x) for x in item.get("compliance_risks") or [] if str(x).strip()],
        ))
    if len(reactions) != len(segments):
        raise InvalidModelOutput("simulation did not return every requested segment")
    angles = data.get("recommended_angles")
    if not isinstance(angles, list) or not angles:
        raise InvalidModelOutput("recommended_angles is missing")
    return {
        "segment_reactions": reactions,
        "recommended_angles": [str(item).strip() for item in angles if str(item).strip()],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def parse_translation(data: Any, *, target_lang: str) -> dict:
    if not isinstance(data, dict):
        raise InvalidModelOutput("translation response is not an object")
    translated = _require_text(data, "translated_text")
    detected = _require_text(data, "detected_lang")
    if len(detected) > 12:
        raise InvalidModelOutput("detected_lang is not a language code")
    breakdown = data.get("breakdown")
    if not isinstance(breakdown, dict):
        raise InvalidModelOutput("breakdown is missing")
    cleaned = {}
    for key in ("hook", "problem", "solution", "cta"):
        cleaned[key] = _require_text(breakdown, key)
    lowered = translated.lower()
    if "naturia" in lowered or "parasite cleanse" in lowered or "بيوفيلم" in translated:
        raise InvalidModelOutput("translation matched a removed canned template")
    return {
        "status": "ok",
        "target_lang": target_lang,
        "detected_lang": detected,
        "translated_text": translated,
        "breakdown": cleaned,
        "charged": False,
    }


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


def narrative_uses_only_facts(text: str, facts: str) -> bool:
    """Reject a narrative that introduces digits the factual brief does not contain."""
    import re
    fact_numbers = set(re.findall(r"\d+(?:\.\d+)?", facts or ""))
    for number in re.findall(r"\d+(?:\.\d+)?", text or ""):
        if number not in fact_numbers:
            return False
    return True
