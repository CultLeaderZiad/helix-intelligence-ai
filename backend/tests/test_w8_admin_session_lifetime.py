"""W8: admin sessions expire sooner than customer sessions."""
from __future__ import annotations

import types

from jose import jwt

from app.core.config import settings
from app.services import auth_service


def _lifetime_minutes(user) -> float:
    claims = jwt.get_unverified_claims(auth_service.session_token_for(user))
    return (claims["exp"] - claims["iat"]) / 60


def _user(**kw):
    base = {"id": "u1", "role": "customer", "is_platform_admin": False, "signup_metadata": {"token_version": 3}}
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_customers_keep_the_normal_lifetime():
    assert abs(_lifetime_minutes(_user()) - settings.ACCESS_TOKEN_EXPIRE_MINUTES) < 1


def test_admins_and_assistants_get_the_short_lifetime():
    for user in (_user(role="admin", is_platform_admin=True), _user(role="assistant-admin"), _user(is_platform_admin=True)):
        assert abs(_lifetime_minutes(user) - settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES) < 1
    assert settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES < settings.ACCESS_TOKEN_EXPIRE_MINUTES


def test_token_keeps_the_session_version():
    claims = jwt.get_unverified_claims(auth_service.session_token_for(_user(role="admin")))
    assert claims["ver"] == 3 and claims["sub"] == "u1"
