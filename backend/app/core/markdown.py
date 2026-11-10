"""Markdown views of read routes, for AI agents ("competitor ads your agents can read").

A read route answers in Markdown when the client sends
``Accept: text/markdown``, adds ``?format=md``, or calls the ``.md`` form of
the route. The labels are the same honest ones the UI uses: unknown run length
is "unknown" (never 0), the score is a text rubric, reach appears only for
rows from Meta's official Ad Library API.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from fastapi import Request
from fastapi.responses import Response

MEDIA_TYPE = "text/markdown; charset=utf-8"
LEGEND = (
    "_Run length comes from the Ad Library start date (\"unknown\" when the source "
    "gives none). The rubric scores the ad text only; it is not a performance "
    "prediction. Reach is shown only for rows from Meta's official Ad Library API._"
)


def split_md(value: str) -> tuple[str, bool]:
    """``"abc.md"`` -> ``("abc", True)``; anything else unchanged."""
    if value.endswith(".md") and len(value) > 3:
        return value[:-3], True
    return value, False


def wants_markdown(request: Optional[Request], forced: bool = False) -> bool:
    if forced:
        return True
    if request is None:
        return False
    if (request.query_params.get("format") or "").lower() in ("md", "markdown"):
        return True
    accept = (request.headers.get("accept") or "").lower()
    return "text/markdown" in accept


def response(text: str) -> Response:
    return Response(content=text, media_type=MEDIA_TYPE, headers={"Vary": "Accept"})


def _get(obj: Any, *path: str) -> Any:
    for key in path:
        if obj is None:
            return None
        obj = obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
    return obj


def _cell(value: Any, limit: int = 120) -> str:
    if value is None or value == "":
        return "—"
    text = " ".join(str(value).split())
    text = text.replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def run_length(days: Any) -> str:
    return "unknown" if days is None else f"{int(days)} days"


def _rubric(item: Any) -> Optional[float]:
    value = _get(item, "text_rubric_score")
    if value is None:
        value = _get(item, "scores", "composite")
    return value


def _reach(item: Any) -> Optional[int]:
    value = _get(item, "impressions_est")
    if value is None:
        value = _get(item, "metrics", "impressions_est")
    return value


def ads_table(items: Iterable[Any]) -> str:
    rows = [
        "| Brand | Headline | Running for | Text rubric | Reach (Meta official) | Ad Library link | id |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in items:
        rubric = _rubric(item)
        reach = _reach(item)
        link = _get(item, "permalink")
        rows.append("| " + " | ".join([
            _cell(_get(item, "brand_name")),
            _cell(_get(item, "headline") or _get(item, "body"), 90),
            run_length(_get(item, "days_active")),
            "—" if rubric is None else f"{float(rubric):.1f}/10",
            "—" if reach is None else f"up to {int(reach):,}",
            f"[open]({link})" if link else "—",
            _cell(_get(item, "id"), 40),
        ]) + " |")
    return "\n".join(rows)


def ads_document(title: str, items: list, *, meta: Optional[list[str]] = None) -> str:
    parts = [f"# {_cell(title, 200)}", ""]
    parts += [f"- {line}" for line in (meta or [])]
    if meta:
        parts.append("")
    parts += [ads_table(items) if items else "_No ads._", "", LEGEND, ""]
    return "\n".join(parts)


def ad_document(item: Any) -> str:
    rubric = _rubric(item)
    reach = _reach(item)
    lines = [
        f"# {_cell(_get(item, 'headline') or 'Ad', 200)}",
        "",
        f"- Brand: {_cell(_get(item, 'brand_name'))}",
        f"- Platform: {_cell(_get(item, 'platform'))}",
        f"- Format: {_cell(_get(item, 'format'))}",
        f"- Running for: {run_length(_get(item, 'days_active'))}",
        f"- First seen: {_cell(_get(item, 'first_seen'))}",
        f"- Last seen: {_cell(_get(item, 'last_seen'))}",
        f"- Text rubric: {'—' if rubric is None else f'{float(rubric):.1f}/10'}",
        f"- Reach (Meta official only): {'—' if reach is None else f'up to {int(reach):,}'}",
        f"- Landing domain: {_cell(_get(item, 'landing_domain'))}",
        f"- Ad Library link: {_get(item, 'permalink') or '—'}",
        f"- id: {_cell(_get(item, 'id'))}",
        "",
        "## Body",
        "",
        (_get(item, "body") or "—").strip(),
        "",
        f"**CTA:** {_cell(_get(item, 'cta'))}",
        "",
        LEGEND,
        "",
    ]
    return "\n".join(lines)


_EVENT_LABEL = {"new_ad": "New ad", "killed_ad": "Stopped running", "copy_changed": "Copy changed"}


def events_document(events: list) -> str:
    parts = ["# Monitor changes", ""]
    if not events:
        return "\n".join(parts + ["_No changes recorded yet. The first run of a monitor records a baseline._", ""])
    parts += ["| When | Change | Headline | Landing domain | Monitor | Ad id |", "|---|---|---|---|---|---|"]
    for event in events:
        parts.append("| " + " | ".join([
            _cell(_get(event, "created_at"), 25),
            _EVENT_LABEL.get(_get(event, "type"), _cell(_get(event, "type"))),
            _cell(_get(event, "headline") or _get(event, "body"), 90),
            _cell(_get(event, "landing_domain")),
            _cell(_get(event, "monitor_id"), 40),
            _cell(_get(event, "creative_id"), 40),
        ]) + " |")
    return "\n".join(parts + [""])
