"""
UI mode -> media category registry for Create.

Historically mapped UI modes to Higgsfield model slugs; Higgsfield has been
removed, so this only tracks whether a mode produces an image or a video —
the one piece of information create_media_job still needs to route to
Gemini (image) vs Pollinations (video).
"""

from typing import Dict, Any

MODE_OUTPUT_TYPES: Dict[str, str] = {
    "premium_ad": "image",
    "quick_concept": "image",
    "cinematic_ad": "image",
    "storyboard": "image",
    "quick_video": "video",
    "premium_video": "video",
    "before_after": "video",
    "controlled_video": "video",
    "image": "image",
    "video": "video",
}

DEFAULT_MODE = "premium_ad"


def resolve_mode_spec(mode: str = None) -> Dict[str, Any]:
    """Returns {"output_type": "image"|"video"} for a given UI mode."""
    key = (mode or DEFAULT_MODE).lower()
    output_type = MODE_OUTPUT_TYPES.get(key, "image")
    return {"output_type": output_type}
