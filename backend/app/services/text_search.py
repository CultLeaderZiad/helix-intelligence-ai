"""Postgres full-text search over the workspace's own ads (0 provider records).

One document per row: brand, headline, body, CTA and landing domain, indexed
with both the ``simple`` config (any language, exact words) and ``arabic``
(Arabic stemming). The query is parsed the same two ways and OR-ed, so English,
Arabic and mixed queries all match. ``websearch_to_tsquery`` accepts free text
("quoted phrases", -exclusions) and never raises on user input.

The expressions below must stay byte-for-byte equal to the GIN indexes in
migration ``f2b4c6d8e0a1`` or Postgres will not use them
(tests/test_w9_archive_search.py checks this).
"""
from __future__ import annotations

from sqlalchemy import text

FTS_COLUMNS = ("brand_name", "headline", "body", "cta", "landing_domain")
MAX_QUERY_LENGTH = 200


def document_sql(table: str) -> str:
    joined = " || ' ' || ".join(f"coalesce({table}.{col}, '')" for col in FTS_COLUMNS)
    return f"(to_tsvector('simple'::regconfig, {joined}) || to_tsvector('arabic'::regconfig, {joined}))"


QUERY_SQL = "(websearch_to_tsquery('simple'::regconfig, :fts_q) || websearch_to_tsquery('arabic'::regconfig, :fts_q))"


def clean_query(q: str | None) -> str:
    return " ".join((q or "").split())[:MAX_QUERY_LENGTH]


def matches(table: str, q: str):
    return text(f"{document_sql(table)} @@ {QUERY_SQL}").bindparams(fts_q=q)


def rank(table: str, q: str):
    return text(f"ts_rank({document_sql(table)}, {QUERY_SQL}) DESC").bindparams(fts_q=q)
