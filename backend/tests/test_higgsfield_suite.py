import asyncio
import os
import sys

# Ensure backend directory is on PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.media.higgsfield_registry import (
    get_base_url,
    resolve_capability,
    resolve_endpoint_url,
    list_available_capabilities,
    SEMANTIC_CAPABILITIES,
)
from app.services.media.higgsfield_provider import HiggsfieldProvider

def test_centralized_base_url():
    """Verify HIGGSFIELD_BASE_URL defaults to platform.higgsfield.ai without trailing slashes."""
    base_url = get_base_url()
    assert "platform.higgsfield.ai" in base_url
    assert not base_url.endswith("/")
    print("[PASS] test_centralized_base_url passed")

def test_semantic_capability_resolution():
    """Verify semantic capability names map to correct Higgsfield models."""
    soul2 = resolve_capability("IMAGE_PREMIUM")
    assert soul2["provider_model_slug"] == "higgsfield-ai/soul/v2/standard"
    assert soul2["output_type"] == "image"
    assert soul2["base_credits"] == 3.0

    dop_turbo = resolve_capability("VIDEO_FAST")
    assert dop_turbo["provider_model_slug"] == "higgsfield-ai/dop/turbo"
    assert dop_turbo["output_type"] == "video"
    assert dop_turbo["base_credits"] == 8.0

    # Aliases
    assert resolve_capability("premium_ad")["provider_model_slug"] == "higgsfield-ai/soul/v2/standard"
    assert resolve_capability("quick_concept")["provider_model_slug"] == "higgsfield-ai/popcorn/auto"
    assert resolve_capability("quick_video")["provider_model_slug"] == "higgsfield-ai/dop/turbo"
    print("[PASS] test_semantic_capability_resolution passed")

def test_endpoint_url_resolution():
    """Verify endpoint URL points to centralized base URL and correct slug."""
    soul2_spec = resolve_capability("IMAGE_PREMIUM")
    url = resolve_endpoint_url(soul2_spec)
    assert url == "https://platform.higgsfield.ai/higgsfield-ai/soul/v2/standard"

    popcorn_spec = resolve_capability("IMAGE_FAST")
    url = resolve_endpoint_url(popcorn_spec)
    assert url == "https://platform.higgsfield.ai/higgsfield-ai/popcorn/auto"
    print("[PASS] test_endpoint_url_resolution passed")

def test_auth_headers_format():
    """Verify Authorization header format uses 'Key <KEY_ID>:<KEY_SECRET>'."""
    provider = HiggsfieldProvider()
    if provider.is_configured:
        headers = provider.headers
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Key ")
        assert ":" in headers["Authorization"]
        assert headers["Content-Type"] == "application/json"
    print("[PASS] test_auth_headers_format passed")

def test_available_capabilities_list():
    """Verify the catalogue returns all 8 required capabilities."""
    catalogue = list_available_capabilities()
    assert len(catalogue) == 8
    slugs = [c["provider_model_slug"] for c in catalogue]
    assert "higgsfield-ai/soul/v2/standard" in slugs
    assert "higgsfield-ai/popcorn/auto" in slugs
    assert "higgsfield-ai/soul/cinema" in slugs
    assert "higgsfield-ai/dop/turbo" in slugs
    assert "higgsfield-ai/dop/standard" in slugs
    print("[PASS] test_available_capabilities_list passed")

async def test_health_check_structure():
    """Verify health check response envelope never leaks raw keys."""
    provider = HiggsfieldProvider()
    health = await provider.get_health()
    assert "provider" in health
    assert health["provider"] == "higgsfield"
    assert "configured" in health
    assert "authenticated" in health
    assert "base_url" in health
    # Verify no credentials leaked
    assert "HF_API_KEY_SECRET" not in str(health)
    assert "Authorization" not in str(health)
    print("[PASS] test_health_check_structure passed")

if __name__ == "__main__":
    print("Running Higgsfield Test Suite...")
    test_centralized_base_url()
    test_semantic_capability_resolution()
    test_endpoint_url_resolution()
    test_auth_headers_format()
    test_available_capabilities_list()
    asyncio.run(test_health_check_structure())
    print("\n=======================================================")
    print("ALL 6 HIGGSFIELD SUITE UNIT TESTS PASSED (100% SUCCESS)")
    print("=======================================================")
