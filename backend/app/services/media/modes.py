"""Media mode & capability catalogue (provider-neutral).

Formerly `higgsfield_registry`. The Higgsfield provider was removed from the
app, but Create, the quota/metering layer (which reads `output_type`), and
`GET /media/models` all still resolve modes through this catalogue - so it
stays, stripped of provider slugs and endpoints.

Generation is served by **Gemini** (managed key or BYOK), with **Pollinations**
as the fallback for video/image.
"""

from typing import Any, Dict, List, Optional

SEMANTIC_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "IMAGE_FAST": {
        "title": "Fast Image (Ideation)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "1:1", "quality": "standard"},
    },
    "IMAGE_PREMIUM": {
        "title": "Premium Image (Commercial Ad Still)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "1:1", "quality": "high"},
    },
    "IMAGE_CINEMATIC": {
        "title": "Cinematic Image (Editorial & Luxury)",
        "operation_type": "text-to-image",
        "output_type": "image",
        "base_credits": 3.0,
        "default_params": {"aspect_ratio": "16:9", "quality": "ultra"},
    },
    "VIDEO_FAST": {
        "title": "Fast Video (Rapid Social Motion)",
        "operation_type": "text-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
    },
    "VIDEO_STANDARD": {
        "title": "Standard Video (Commercial Video)",
        "operation_type": "text-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
    },
    "VIDEO_FIRST_LAST_FAST": {
        "title": "Before/After Video (Fast Transition)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
    "VIDEO_FIRST_LAST_STANDARD": {
        "title": "Before/After Video (Keyframed Motion)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
    "VIDEO_FIRST_LAST_LITE": {
        "title": "Before/After Video (Preview)",
        "operation_type": "image-to-video",
        "output_type": "video",
        "base_credits": 8.0,
        "default_params": {"aspect_ratio": "9:16", "duration": 5},
        "requires_inputs": ["start_image_url", "end_image_url"],
    },
}

# UI mode -> capability. Legacy provider slugs are kept as aliases so old job
# rows (whose parameters.mode holds a slug) still resolve to a mode spec.
MODE_ALIASES: Dict[str, str] = {
    "quick_concept": "IMAGE_FAST",
    "premium_ad": "IMAGE_PREMIUM",
    "cinematic_ad": "IMAGE_CINEMATIC",
    "storyboard": "IMAGE_FAST",
    "quick_video": "VIDEO_FAST",
    "premium_video": "VIDEO_STANDARD",
    "before_after": "VIDEO_FIRST_LAST_FAST",
    "controlled_video": "VIDEO_FIRST_LAST_STANDARD",
    # Legacy slug aliases (old jobs only - no provider remains).
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


def resolve_capability(mode_or_capability: Optional[str] = None) -> Dict[str, Any]:
    """Resolve a mode/alias to its capability spec, with defaults."""
    if not mode_or_capability:
        return {"capability": DEFAULT_CAPABILITY, **SEMANTIC_CAPABILITIES[DEFAULT_CAPABILITY]}
    if mode_or_capability in SEMANTIC_CAPABILITIES:
        return {"capability": mode_or_capability, **SEMANTIC_CAPABILITIES[mode_or_capability]}
    cap_key = MODE_ALIASES.get(str(mode_or_capability).lower(), DEFAULT_CAPABILITY)
    return {"capability": cap_key, **SEMANTIC_CAPABILITIES[cap_key]}


def list_available_capabilities() -> List[Dict[str, Any]]:
    """Catalogue for `GET /media/models` (frontend contracts)."""
    return [{"capability": k, **v} for k, v in SEMANTIC_CAPABILITIES.items()]


# Backward-compatibility aliases (imported across the media stack).
resolve_mode_spec = resolve_capability
MODEL_REGISTRY = SEMANTIC_CAPABILITIES
