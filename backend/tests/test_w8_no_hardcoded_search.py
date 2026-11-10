"""No curated search targets, and the scale caps stay finite."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import NullPool, QueuePool

from app.services.query_bounds import (
    ADMIN_LIST_CAP,
    MAX_PAGE_SIZE,
    MONITOR_LIST_CAP,
    pagination_bounds,
)


def test_pagination_bounds_cap_page_size_and_reject_junk():
    assert pagination_bounds(2, 500) == (MAX_PAGE_SIZE, MAX_PAGE_SIZE)
    with pytest.raises(HTTPException):
        pagination_bounds(0, 10)
    with pytest.raises(HTTPException):
        pagination_bounds(1, 0)


def test_plain_list_caps_are_finite():
    assert 1 <= ADMIN_LIST_CAP <= 500
    assert 1 <= MONITOR_LIST_CAP <= MAX_PAGE_SIZE


def test_relevance_uses_the_query_not_a_named_list():
    from app.services.discover_service import _is_creative_relevant

    ad = SimpleNamespace(
        headline="fresh sneakers",
        body="stream tonight",
        brand_name="local shop",
        landing_domain="shop.example",
        cta="shop",
    )
    assert _is_creative_relevant(ad, "stream tonight") is True
    assert _is_creative_relevant(ad, "unrelatedtoken") is False
    assert _is_creative_relevant(
        ad, "acme", {"disambiguation": {"filtered_categories": ["sneakers"]}}
    ) is False


def test_production_modules_have_no_curated_search_targets():
    root = Path(__file__).resolve().parents[1] / "app"
    banned = (
        "sneako",
        "ishowspeed",
        "adin ross",
        "kai cenat",
        "andrew tate",
        "nike tn",
        "gymshark",
        "brand.com",
        "nike.com",
    )
    hits = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for name in banned:
            if name in text:
                hits.append(f"{path.relative_to(root)}:{name}")
    assert hits == []


def test_api_pool_is_bounded_and_worker_does_not_hold_a_pool():
    from app.core.config import settings
    from app.db.session import engine, worker_engine

    assert isinstance(engine.pool, QueuePool)
    assert isinstance(worker_engine.pool, NullPool)
    assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW
    assert engine.pool._timeout == settings.DB_POOL_TIMEOUT_S
    assert engine.pool._recycle == settings.DB_POOL_RECYCLE_S
    config_src = Path(__file__).resolve().parents[1].joinpath("app/core/config.py").read_text()
    assert 'os.getenv("DB_POOL_SIZE", "5")' in config_src
    assert 'os.getenv("DB_MAX_OVERFLOW", "5")' in config_src
    assert 'os.getenv("DB_POOL_TIMEOUT_S", "10")' in config_src
    assert "statement_cache_size" in Path(__file__).resolve().parents[1].joinpath("app/db/session.py").read_text()
