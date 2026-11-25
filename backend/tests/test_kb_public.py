"""Knowledge base: any signed-in user can read enabled articles; only admins can change anything."""
from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from app.api.routers import knowledge_base as kb
from app.core.deps import get_current_full_admin, get_current_user
from app.services import kb_service


def _deps(route):
    return {d.call for d in route.dependant.dependencies}


def test_public_routes_are_read_only_and_need_a_signed_in_user():
    assert {tuple(sorted(r.methods)) for r in kb.public_router.routes} == {("GET",)}
    for route in kb.public_router.routes:
        assert get_current_user in _deps(route), route.path
        assert get_current_full_admin not in _deps(route), route.path


def test_every_admin_route_still_needs_a_full_admin():
    assert kb.router.routes
    for route in kb.router.routes:
        assert get_current_full_admin in _deps(route), route.path


def test_public_view_leaks_no_uploader_checksum_or_file_name():
    class Doc:
        id, title, version, created_at = "d1", "Pricing guide", 3, None
        uploaded_by, checksum, filename, status = "admin-1", "abc", "secret.md", "enabled"

    assert kb_service._public_view(Doc()) == {"id": "d1", "title": "Pricing guide", "version": 3, "updated_at": None}


@pytest.mark.asyncio
async def test_a_disabled_or_missing_article_is_a_404():
    class Db:
        def __init__(self, doc):
            self.doc = doc

        async def get(self, model, key):
            return self.doc

    class Disabled:
        status = "disabled"

    for doc in (None, Disabled()):
        with pytest.raises(HTTPException) as exc:
            await kb_service.public_document(Db(doc), "x")
        assert exc.value.status_code == 404


def test_search_only_looks_at_enabled_documents():
    assert "d.status = 'enabled'" in inspect.getsource(kb_service.search)
