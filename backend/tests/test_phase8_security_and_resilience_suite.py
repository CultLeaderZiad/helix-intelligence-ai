import io
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from starlette.requests import Request
from fastapi import HTTPException

from app.core.config import settings
from app.middleware.rate_limit import RateLimitMiddleware, _rules, _is_valid_public_ip
from app.services.scrapling_engine import robots_allowed
from app.services.leadgen_pipeline import parse_sitemap
from app.services.ai.pollinations_provider import (
    PollinationsProvider,
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
)
from app.api.routers.scout import sanitize_csv_cell as scout_sanitize_csv
from app.api.routers.leadgen import sanitize_csv_cell as leadgen_sanitize_csv


# ============================================================================
# F58: Rate Limiting & Client IP Extraction
# ============================================================================

def test_f58_is_valid_public_ip():
    assert _is_valid_public_ip("127.0.0.1") is False
    assert _is_valid_public_ip("10.0.0.1") is False
    assert _is_valid_public_ip("172.16.0.1") is False
    assert _is_valid_public_ip("192.168.1.1") is False
    assert _is_valid_public_ip("::1") is False
    assert _is_valid_public_ip("8.8.8.8") is True
    assert _is_valid_public_ip("1.1.1.1") is True
    assert _is_valid_public_ip("93.184.216.34") is True
    assert _is_valid_public_ip("attacker.spoofed.ip") is False


def test_f58_client_ip_precedence():
    middleware = RateLimitMiddleware(app=MagicMock())

    # Forwarding headers are ignored unless the TCP peer is a trusted proxy.
    scope = {
        "type": "http",
        "headers": [
            (b"cf-connecting-ip", b"93.184.216.34"),
            (b"true-client-ip", b"93.184.216.35"),
            (b"x-forwarded-for", b"93.184.216.36"),
        ],
        "client": ("192.168.1.50", 12345),
    }
    assert middleware._client_ip(Request(scope)) == "192.168.1.50"

    with patch.object(settings, "TRUSTED_PROXY_CIDRS", "192.168.0.0/16,10.0.0.0/8"):
        assert middleware._client_ip(Request(scope)) == "93.184.216.34"

        scope2 = {
            "type": "http",
            "headers": [
                (b"true-client-ip", b"93.184.216.35"),
                (b"x-forwarded-for", b"93.184.216.36"),
            ],
            "client": ("192.168.1.50", 12345),
        }
        assert middleware._client_ip(Request(scope2)) == "93.184.216.35"

        # Rightmost untrusted hop, so a prepended spoof does not win.
        scope3 = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"1.2.3.4, 93.184.216.34"),
            ],
            "client": ("10.0.0.1", 12345),
        }
        assert middleware._client_ip(Request(scope3)) == "93.184.216.34"

    scope4 = {
        "type": "http",
        "headers": [],
        "client": ("203.0.113.99", 12345),
    }
    assert middleware._client_ip(Request(scope4)) == "203.0.113.99"


def test_f58_rate_limit_rules_and_normalization():
    rule_paths = [r[0] for r in _rules()]
    assert "/api/leadgen/jobs" in rule_paths
    assert "/api/discovery/jobs" in rule_paths
    assert "/api/auth/sign-in" in rule_paths


# ============================================================================
# F66: Unbounded Network / Memory Ceilings
# ============================================================================

def test_f66_robots_allowed_ssrf_and_timeout():
    # Private / internal URL should fail open without network call
    assert robots_allowed("http://127.0.0.1:8000/some-path") is True
    assert robots_allowed("http://169.254.169.254/latest/meta-data") is True


def test_f66_parse_sitemap_recursion_and_visited_guards():
    # If sitemap points to itself, visited set prevents recursion loop
    fake_sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <sitemap>
          <loc>https://example.com/sitemap.xml</loc>
       </sitemap>
    </sitemapindex>"""

    with patch("app.services.security_service.safe_http_get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_sitemap_xml
        mock_get.return_value = mock_resp

        # Should terminate cleanly with 0 URLs returned, not an infinite loop / RecursionError
        result = parse_sitemap("https://example.com/sitemap.xml", limit=10, max_depth=2)
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_f66_pollinations_streaming_chunk_limits():
    provider = PollinationsProvider()

    # Mock client stream exceeding MAX_IMAGE_BYTES
    async def fake_aiter_bytes(chunk_size):
        # Yield chunks that sum to more than 15MB
        chunk = b"X" * (5 * 1024 * 1024)
        for _ in range(4):  # 20MB total > 15MB
            yield chunk

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.aiter_bytes = fake_aiter_bytes

    class FakeStreamContext:
        async def __aenter__(self):
            return mock_resp
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class FakeClient:
        def stream(self, *args, **kwargs):
            return FakeStreamContext()
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        with pytest.raises(ValueError, match="exceeds maximum allowed size of 15MB"):
            await provider.generate_image(prompt="test image")


# ============================================================================
# F67: CSV Formula Injection Sanitization (OWASP CWE-1236)
# ============================================================================

def test_f67_csv_formula_injection_defense():
    dangerous_inputs = [
        "=SUM(A1:A10)",
        "+cmd|' /C calc'!A0",
        "-2+3*cmd",
        "@evil_lookup()",
        "\tmalicious_tab",
        "\rmalicious_cr",
    ]

    safe_inputs = [
        "Normal Company Name",
        "hello@example.com",  # @ is inside string, not at start
        "123 Main Street",
        12345,
        0,
        None,
    ]

    for val in dangerous_inputs:
        sanitized_scout = scout_sanitize_csv(val)
        sanitized_leadgen = leadgen_sanitize_csv(val)
        assert sanitized_scout.startswith("'"), f"Scout failed on: {val}"
        assert sanitized_leadgen.startswith("'"), f"Leadgen failed on: {val}"

    for val in safe_inputs:
        if val is None:
            assert scout_sanitize_csv(val) == ""
            assert leadgen_sanitize_csv(val) == ""
        else:
            assert scout_sanitize_csv(val) == val
            assert leadgen_sanitize_csv(val) == val
