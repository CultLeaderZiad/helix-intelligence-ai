"""W9: the temporary forwarding-header probe logs only probes, masked."""
from __future__ import annotations

from app.middleware.forwarding_probe import describe, mask


def test_ip_addresses_are_masked_and_order_is_kept():
    assert mask("203.0.113.1, 197.37.196.59") == "203.0.x.x, 197.37.x.x"
    assert mask("for=198.51.100.7;proto=https") == "for=198.51.x.x;proto=https"
    assert "196.59" not in mask("197.37.196.59")
    assert mask("2001:db8:85a3::8a2e:370:7334") == "2001:db8:x"


def test_only_probe_requests_on_health_are_described():
    headers = {"x-forwarded-for": "203.0.113.1, 197.37.196.59", "cf-connecting-ip": "197.37.196.59"}
    line = describe("/api/health", "probe=claude-1", headers, "127.0.0.1")
    assert line and "probe=claude-1" in line and "peer=127.0.x.x" in line
    assert "203.0.x.x, 197.37.x.x" in line and "cf-connecting-ip" in line
    assert "196.59" not in line
    assert describe("/api/health", "", headers, "127.0.0.1") is None
    assert describe("/api/auth/sign-in", "probe=x", headers, "127.0.0.1") is None
    assert describe("/api/health", "probe=<script>", headers, "127.0.0.1") is None
