"""Postgres full-text search over the workspace's own ads (0 provider records).

One document per row: brand, headline, body, CTA and landing domain, indexed
with both the ``simple`` config (any language, exact words) and ``arabic``
(Arabic stemming). Each config is matched against its own document and the results are
OR-ed, so English, Arabic and mixed queries all match, and a quoted phrase
never matches across the two representations. ``websearch_to_tsquery`` accepts free text
("quoted phrases", -exclusions) and never raises on user input.

The expressions below must stay byte-for-byte equal to the GIN indexes in
migration ``b5d7f9a1c3e6`` or Postgres will not use them
(tests/test_w9_archive_search.py checks this).
"""
from __future__ import annotations

import re

from sqlalchemy import text

FTS_COLUMNS = ("brand_name", "headline", "body", "cta", "landing_domain")
MAX_QUERY_LENGTH = 200


CONFIGS = ("simple", "arabic")


def document_sql(table: str, config: str) -> str:
    """One config's document. Kept separate per config so a quoted phrase can
    only match inside one representation, never across the two."""
    joined = " || ' ' || ".join(f"coalesce({table}.{col}, '')" for col in FTS_COLUMNS)
    return f"to_tsvector('{config}'::regconfig, {joined})"


def query_sql(config: str) -> str:
    return f"websearch_to_tsquery('{config}'::regconfig, :fts_q)"


def clean_query(q: str | None) -> str:
    return " ".join((q or "").split())[:MAX_QUERY_LENGTH]


_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})
_TASHKEEL = re.compile("[ً-ْٰـ]")  # harakat, superscript alef, tatweel


def normalize_arabic(text: str) -> str:
    """Light Arabic normalisation: alef forms -> ا, ة -> ه, ى -> ي, strip tashkeel and tatweel."""
    return _TASHKEEL.sub("", text or "").translate(_ALEF)


def expand_query(q: str) -> str:
    """The query, OR its normalised spelling when that differs (websearch syntax).

    Documents are not rewritten, so both spellings are searched: "مكتبة" also
    finds "مكتبه", and "إعلان" also finds "اعلان". The arabic config already
    stems; this mainly helps the simple config and words the stemmer leaves.
    """
    norm = normalize_arabic(q)
    return q if not q or norm == q else f"{q} or {norm}"


def _pairs():
    # Every document config against every query config: an Arabic word can
    # stem differently as a document and as a query ("الهدايا" vs "هدايا"),
    # so each vector is tried with both parsings. Each test stays inside one
    # vector, so a quoted phrase still never spans the two.
    return [(d, qc) for d in CONFIGS for qc in CONFIGS]


def matches(table: str, q: str):
    clause = " OR ".join(f"({document_sql(table, d)} @@ {query_sql(qc)})" for d, qc in _pairs())
    return text(f"({clause})").bindparams(fts_q=expand_query(q))


def rank(table: str, q: str):
    score = " + ".join(f"ts_rank({document_sql(table, d)}, {query_sql(qc)})" for d, qc in _pairs())
    return text(f"({score}) DESC").bindparams(fts_q=expand_query(q))
