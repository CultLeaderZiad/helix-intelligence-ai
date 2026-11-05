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
    assert "/api/discovery/jobs" in rule_paths
    assert "/api/auth/sign-in" in rule_paths


# ============================================================================
# F66: Unbounded Network / Memory Ceilings
# ============================================================================







# ============================================================================
# F67: CSV Formula Injection Sanitization (OWASP CWE-1236)
# ============================================================================

