"""Competitor site snapshot (no network, no database)."""
import asyncio

import pytest
from fastapi import HTTPException

from app.services import competitor_snapshot as cs

HTML = """<html><head><title> Acme  Shoes </title>
<meta name="description" content="Fast shoes &amp; more"><meta property="og:site_name" content="Acme"></head>
<body><a href="/pricing">Plans</a><a href="https://www.instagram.com/acme/">ig</a>
<a href="https://evil.com/pricing">x</a><a href="javascript:alert(1)">j</a><a href="https://facebook.com/">home</a></body></html>"""


def test_parse_home_reads_only_what_the_page_says():
    out = cs.parse_home(HTML, "https://acme.com/")
    assert out["title"] == "Acme Shoes" and out["description"] == "Fast shoes & more" and out["site_name"] == "Acme"
    assert out["social"] == {"Instagram": "https://www.instagram.com/acme/"}  # bare facebook.com is not a profile
    assert out["pages"] == {"pricing": "https://acme.com/pricing"}  # other hosts never count as the site's pages


def test_top_domain_picks_the_most_common_real_domain():
    assert cs.top_domain(["https://www.acme.com/a", "acme.com", "other.com", None, "no dots"]) == "acme.com"
    assert cs.top_domain([None, ""]) is None


def test_no_site_is_a_clear_404():
    with pytest.raises(HTTPException) as e:
        asyncio.run(cs.snapshot("u1", None))
    assert e.value.status_code == 404


def test_daily_allowance_blocks_after_the_limit():
    cs._usage.clear()
    for _ in range(cs.DAILY_LIMIT):
        cs._check_allowance("u2")
    with pytest.raises(HTTPException) as e:
        cs._check_allowance("u2")
    assert e.value.status_code == 429


def test_cached_site_costs_no_allowance(monkeypatch):
    cs._usage.clear()
    cs._cache["cached.com"] = {"at": __import__("time").monotonic(), "data": {"domain": "cached.com"}}
    out = asyncio.run(cs.snapshot("u3", "cached.com"))
    assert out["cached"] is True and "u3" not in cs._usage
