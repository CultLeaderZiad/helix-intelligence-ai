"""
Higgsfield Model & Semantic Registry for Helix Intelligence.

Maps HELIX semantic capabilities and UI modes to official Higgsfield API
model endpoints on platform.higgsfield.ai.
"""

from typing import Dict, Any, Optional, List
from app.core.config import settings

# Semantic Capability Mappings
SEMANTIC_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "IMAGE_FAST": {
        "provider_model_slug": "higgsfield-ai/popcorn/auto",
        "title": "Popcorn Auto (Fast Ideation)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "1:1", "quality": "standard"},
    },
    "IMAGE_PREMIUM": {
        "provider_model_slug": "higgsfield-ai/soul/v2/standard",
        "title": "Soul v2 Standard (Commercial Ad Still)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "1:1", "quality": "high"},
    },
    "IMAGE_CINEMATIC": {
        "provider_model_slug": "higgsfield-ai/soul/cinema",
        "title": "Soul Cinema (Editorial & Luxury)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "16:9", "quality": "ultra"},
    },
    "VIDEO_FAST": {
        "provider_model_slug": "higgsfield-ai/dop/turbo",
        "title": "DoP Turbo (Rapid Social Motion)",
        "operation_type": "text-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
    },
    "VIDEO_STANDARD": {
        "provider_model_slug": "higgsfield-ai/dop/standard",
        "title": "DoP Standard (Commercial Video)",
        "operation_type": "text-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
    },
    "VIDEO_FIRST_LAST_FAST": {
        "provider_model_slug": "higgsfield-ai/dop/turbo/first-last-frame",
        "title": "DoP Turbo FLF (Before -> After Transition)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
    "VIDEO_FIRST_LAST_STANDARD": {
        "provider_model_slug": "higgsfield-ai/dop/standard/first-last-frame",
        "title": "DoP Standard FLF (Brand Keyframed Motion)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
    "VIDEO_FIRST_LAST_LITE": {
        "provider_model_slug": "higgsfield-ai/dop/lite/first-last-frame",
        "title": "DoP Lite FLF (Preview Transition)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
}

# UI Mode to Semantic Capability Alias Map
MODE_ALIASES: Dict[str, str] = {
    # UI Mode Names
    "quick_concept": "IMAGE_FAST",
    "premium_ad": "IMAGE_PREMIUM",
    "cinematic_ad": "IMAGE_CINEMATIC",
    "storyboard": "IMAGE_FAST",
    "quick_video": "VIDEO_FAST",
    "premium_video": "VIDEO_STANDARD",
    "before_after": "VIDEO_FIRST_LAST_FAST",
    "controlled_video": "VIDEO_FIRST_LAST_STANDARD",
    
    # Direct model slug aliases
    "higgsfield-ai/popcorn/auto": "IMAGE_FAST",
    "higgsfield-ai/soul/v2/standard": "IMAGE_PREMIUM",
    "higgsfield-ai/soul/cinema": "IMAGE_CINEMATIC",
    "higgsfield-ai/dop/turbo": "VIDEO_FAST",
    "higgsfield-ai/dop/standard": "VIDEO_STANDARD",
    "higgsfield-ai/dop/turbo/first-last-frame": "VIDEO_FIRST_LAST_FAST",
    "higgsfield-ai/dop/standard/first-last-frame": "VIDEO_FIRST_LAST_STANDARD",
    "higgsfield-ai/dop/lite/first-last-frame": "VIDEO_FIRST_LAST_LITE",
    
    # Generic fallbacks
    "image": "IMAGE_PREMIUM",
    "video": "VIDEO_FAST",
}

DEFAULT_CAPABILITY = "IMAGE_PREMIUM"

def get_base_url() -> str:
    """Returns the centralized Higgsfield base URL without trailing slash."""
    raw = getattr(settings, "HIGGSFIELD_BASE_URL", "") or "https://platform.higgsfield.ai"
    return raw.rstrip("/")

def resolve_capability(mode_or_capability: Optional[str] = None) -> Dict[str, Any]:
    """Resolves semantic capability specification with defaults."""
    if not mode_or_capability:
        return {
            "capability": DEFAULT_CAPABILITY,
            **SEMANTIC_CAPABILITIES[DEFAULT_CAPABILITY]
        }

    # Direct match in semantic capabilities
    if mode_or_capability in SEMANTIC_CAPABILITIES:
        return {
            "capability": mode_or_capability,
            **SEMANTIC_CAPABILITIES[mode_or_capability]
        }

    # Alias match
    cap_key = MODE_ALIASES.get(mode_or_capability.lower(), DEFAULT_CAPABILITY)
    return {
        "capability": cap_key,
        **SEMANTIC_CAPABILITIES[cap_key]
    }

def resolve_endpoint_url(capability_spec: Dict[str, Any]) -> str:
    """Builds the absolute API URL on platform.higgsfield.ai."""
    base_url = get_base_url()
    slug = capability_spec.get("provider_model_slug", "higgsfield-ai/soul/v2/standard").lstrip("/")
    return f"{base_url}/{slug}"

def list_available_capabilities() -> List[Dict[str, Any]]:
    """Returns list of semantic capabilities for frontend and API contracts."""
    return [
        {"capability": k, **v} for k, v in SEMANTIC_CAPABILITIES.items()
    ]
