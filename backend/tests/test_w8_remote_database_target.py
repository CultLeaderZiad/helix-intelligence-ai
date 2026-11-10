"""W8: one explicitly allowlisted remote database outside production.

Hostnames here are fictional (.invalid / made-up Neon endpoint ids).
"""
import pytest

from app.core.origins import validate_database_target

NONPROD = ("development", "test", "staging", "preview")
DEV_HOST = "ep-dev-branch-a1b2c3d4-pooler.c-9.us-east-2.aws.neon.tech"
PROD_HOST = "ep-prod-main-z9y8x7w6-pooler.c-9.us-east-2.aws.neon.tech"


def url(host: str, query: str = "sslmode=require") -> str:
    return f"postgresql+asyncpg://app:secret@{host}/neondb" + (f"?{query}" if query else "")


def check(value: str, environment: str, allowed: str | None = DEV_HOST, production: str | None = PROD_HOST):
    validate_database_target(
        value, environment=environment, allowed_remote_host=allowed, production_host=production
    )


@pytest.mark.parametrize("environment", NONPROD)
def test_loopback_is_still_allowed_with_or_without_an_allowlist(environment):
    for allowed in (None, "", DEV_HOST):
        check("postgresql+asyncpg://u:p@127.0.0.1:5432/helix", environment, allowed=allowed)
        check("postgresql+asyncpg://u:p@localhost/helix", environment, allowed=allowed, production=None)


@pytest.mark.parametrize("environment", NONPROD)
@pytest.mark.parametrize("query", ["sslmode=require", "ssl=require", "sslmode=verify-full", "sslmode=require&channel_binding=require"])
def test_allowlisted_host_with_tls_is_allowed(environment, query):
    check(url(DEV_HOST, query), environment)
    # Exact match is case- and trailing-dot-insensitive, nothing more.
    check(url(DEV_HOST.upper() + ".", query), environment)


@pytest.mark.parametrize("environment", NONPROD)
@pytest.mark.parametrize(
    "host",
    [
        "db.example.invalid",
        DEV_HOST.replace("-pooler", ""),  # the direct name is a different host: not allowlisted
        "evil." + DEV_HOST,
        DEV_HOST.replace(".tech", ".tech.example.invalid"),
        "10.0.0.5",
    ],
)
def test_any_other_remote_host_is_refused(environment, host):
    with pytest.raises(ValueError, match="loopback"):
        check(url(host), environment)


@pytest.mark.parametrize("environment", NONPROD)
def test_remote_host_without_allowlist_is_refused(environment):
    for allowed in (None, ""):
        with pytest.raises(ValueError, match="loopback"):
            check(url(DEV_HOST), environment, allowed=allowed)


@pytest.mark.parametrize("environment", NONPROD)
@pytest.mark.parametrize("query", ["", "sslmode=disable", "sslmode=prefer", "sslmode=allow", "ssl=false", "sslmode=require&ssl=disable"])
def test_non_tls_remote_url_is_refused(environment, query):
    with pytest.raises(ValueError, match="TLS"):
        check(url(DEV_HOST, query), environment)


@pytest.mark.parametrize("environment", NONPROD)
def test_production_endpoint_is_never_accepted_outside_production(environment):
    for allowed in (PROD_HOST, PROD_HOST.replace("-pooler", ""), PROD_HOST.upper()):
        for production in (PROD_HOST, PROD_HOST.replace("-pooler", "")):
            with pytest.raises(ValueError, match="production database endpoint"):
                check(url(allowed), environment, allowed=allowed, production=production)


@pytest.mark.parametrize("environment", NONPROD)
def test_allowlist_fails_closed_without_a_production_host(environment):
    for production in (None, "", "not a host"):
        with pytest.raises(ValueError, match="PRODUCTION_DATABASE_HOST"):
            check(url(DEV_HOST), environment, production=production)


@pytest.mark.parametrize("environment", NONPROD)
def test_allowlisted_host_cannot_be_redirected_by_query_overrides(environment):
    for query in ("sslmode=require&host=db.example.invalid", "sslmode=require&hostaddr=10.0.0.5"):
        with pytest.raises(ValueError, match="override"):
            check(url(DEV_HOST, query), environment)


def test_allowlist_does_not_apply_to_sqlite():
    with pytest.raises(ValueError):
        check(f"sqlite+aiosqlite://{DEV_HOST}/x.db", "development")


@pytest.mark.parametrize(
    "value",
    [
        url(PROD_HOST),
        url(DEV_HOST),
        url("db.example.invalid", ""),
        "postgresql+asyncpg://u:p@127.0.0.1/helix",
    ],
)
def test_production_behaviour_is_unchanged_by_the_new_settings(value):
    # Same result as before W8 (no error) whatever the new settings hold.
    for allowed, production in ((None, None), (DEV_HOST, PROD_HOST), (PROD_HOST, PROD_HOST), ("x.invalid", "")):
        validate_database_target(value, environment="production", allowed_remote_host=allowed, production_host=production)
        validate_database_target(value, environment="production")
