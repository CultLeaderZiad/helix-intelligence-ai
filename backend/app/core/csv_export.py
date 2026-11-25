"""CSV for board export. Cells that start like a formula are neutralised (CSV injection)."""
from __future__ import annotations

import csv
import io
from typing import Any, Iterable

COLUMNS = [
    ("brand_name", "Brand"),
    ("platform", "Platform"),
    ("format", "Format"),
    ("headline", "Headline"),
    ("body", "Body"),
    ("cta", "CTA"),
    ("landing_domain", "Landing domain"),
    ("first_seen", "First seen"),
    ("last_seen", "Last seen"),
    ("days_active", "Days active"),
    ("text_rubric_score", "Text rubric (AI, not performance)"),
    ("permalink", "Ad Library link"),
    ("id", "Helix id"),
]
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def board_csv(items: Iterable[dict]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([label for _, label in COLUMNS])
    for item in items:
        writer.writerow([safe_cell(item.get(key)) for key, _ in COLUMNS])
    return "\ufeff" + out.getvalue()  # BOM so Excel reads Arabic correctly


def filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)[:80] or "board"
    return f"{safe}.csv"
