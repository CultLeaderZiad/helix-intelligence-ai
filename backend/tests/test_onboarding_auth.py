"""Regression coverage for per-user onboarding completion and restart."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.routers.auth import complete_onboarding, restart_onboarding, router
from app.core.deps import get_current_user


def test_onboarding_completion_and_restart_are_persisted_per_user():
    async def run():
        user = SimpleNamespace(id="user-one", has_completed_onboarding=False)
        other_user = SimpleNamespace(id="user-two", has_completed_onboarding=False)
        db = SimpleNamespace(commit=AsyncMock())

        completed = await complete_onboarding(current_user=user, db=db)
        assert completed == {"message": "Onboarding marked as complete"}
        assert user.has_completed_onboarding is True
        assert other_user.has_completed_onboarding is False
        db.commit.assert_awaited_once()

        restarted = await restart_onboarding(current_user=user, db=db)
        assert restarted == {"message": "Onboarding marked as incomplete"}
        assert user.has_completed_onboarding is False
        assert other_user.has_completed_onboarding is False
        assert db.commit.await_count == 2

        await complete_onboarding(current_user=user, db=db)
        assert user.has_completed_onboarding is True
        assert db.commit.await_count == 3

    asyncio.run(run())


def test_onboarding_mutation_routes_require_the_current_user_dependency():
    routes = {route.path: route for route in router.routes}

    for path in ("/session/onboarding/complete", "/session/onboarding/restart"):
        route = routes[path]
        assert "POST" in route.methods
        assert any(dependency.call is get_current_user for dependency in route.dependant.dependencies)
