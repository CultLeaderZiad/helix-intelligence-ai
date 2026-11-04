from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import (
    _dotenv_files_for_environment,
    _parse_cors_origins,
    classified_environment,
    validate_boot_invariants,
)
from app.core.origins import (
    is_loopback_host,
    validate_database_target,
    validate_http_target,
)


def test_preview_is_not_production_and_never_loads_dotenv_files():
    assert classified_environment(SimpleNamespace(ENVIRONMENT="preview")) == "preview"
    assert _dotenv_files_for_environment("preview") is None
    assert _dotenv_files_for_environment("test") is None
    assert _dotenv_files_for_environment("staging") is None
    assert _dotenv_files_for_environment("production") is None
    assert all(Path(path).name == ".env.local" for path in _dotenv_files_for_environment("development"))


def test_nonproduction_http_targets_are_loopback_only():
    assert is_loopback_host("localhost")
    assert is_loopback_host("127.0.0.2")
    assert is_loopback_host("::1")
    for environment in ("development", "test", "staging", "preview"):
        validate_http_target(
            "http://localhost:8000/api", name="API_BASE_URL", environment=environment
        )
        with pytest.raises(ValueError, match="loopback"):
            validate_http_target(
                "https://api.example.invalid", name="API_BASE_URL", environment=environment
            )


def test_production_http_targets_require_public_https_origins():
    parsed = validate_http_target(
        "https://api.example.invalid/v1", name="API_BASE_URL", environment="production"
    )
    assert parsed is not None and parsed.hostname == "api.example.invalid"
    for value in ("http://api.example.invalid", "https://localhost:8000"):
        with pytest.raises(ValueError, match="public HTTPS"):
            validate_http_target(value, name="API_BASE_URL", environment="production")


def test_database_and_cors_defaults_do_not_use_remote_targets():
    validate_database_target(
        "postgresql+asyncpg://test:test@127.0.0.1:5432/helix", environment="development"
    )
    with pytest.raises(ValueError, match="loopback"):
        validate_database_target(
            "postgresql+asyncpg://test:test@db.example.invalid:5432/helix",
            environment="preview",
        )
    assert _parse_cors_origins("", "development") == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert _parse_cors_origins("", "production") == []


def test_production_boot_requires_explicit_app_and_cors_origins():
    config = SimpleNamespace(
        ENVIRONMENT="production",
        PUBLIC_APP_BASE_URL="https://app.example.invalid",
        PUBLIC_API_BASE_URL="/api",
        APP_BASE_URL="https://app.example.invalid",
        NEON_JWKS_URL="",
        NEON_AUTH_URL="",
        NEON_JWT_ISSUER="",
        NEON_JWT_AUDIENCE="",
        R2_PUBLIC_BASE_URL="",
        R2_ENDPOINT_URL="",
        DATABASE_URL="postgresql+asyncpg://test:test@db.example.invalid:5432/helix",
        BACKEND_CORS_ORIGINS="https://app.example.invalid",
        USE_MOCKS=False,
        HELIX_DISPATCH_INLINE=False,
        AUTH_DEV_RESET_RETURN=False,
        SECRET_KEY="s" * 40,
        CREDENTIAL_ENCRYPTION_KEY="c" * 40,
        RESEND_API_KEY="test-key",
        RESEND_FROM="noreply@example.invalid",
        APIFY_ENABLED=False,
        GROQ_MODEL="test-model",
        GEMINI_TEXT_MODEL="test-model",
        GEMINI_IMAGE_MODEL="test-model",
    )
    validate_boot_invariants(config)

    config.APP_BASE_URL = "http://localhost:3000"
    with pytest.raises(RuntimeError, match="APP_BASE_URL"):
        validate_boot_invariants(config)
