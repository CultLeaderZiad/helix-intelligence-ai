"""
Higgsfield Model & Mode Registry for Helix Intelligence.

Maps user-facing creative modes to official Higgsfield API model endpoints,
parameter constraints, and media formats.
"""

from typing import Dict, Any, Optional

# Official Higgsfield Base URL
HF_API_BASE = "https://api.higgsfield.ai"

# Known Models supported on this API account:
# IMAGE:
#   - Popcorn Auto: Fast ideation, storyboard, variations, consistency
#   - Soul 2: Default premium commercial ad still
#   - Soul Cinema: Cinematic, luxury, editorial aesthetics
# VIDEO:
#   - DoP Lite: Cheap preview motion
#   - DoP Turbo: Default fast motion
#   - DoP Standard: High quality video
#   - DoP First-Last-Frame (FLF): Controlled start->end transitions, before->after

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- IMAGE MODES ---
    "quick_concept": {
        "label": "Quick Concept",
        "category": "image",
        "model_id": "popcorn_auto",
        "endpoint": "/higgsfield-ai/popcorn/v1/auto",
        "description": "Fast ideation & concept generation with high consistency.",
        "default_params": {
            "aspect_ratio": "1:1",
            "quality": "standard",
        }
    },
    "premium_ad": {
        "label": "Premium Ad",
        "category": "image",
        "model_id": "soul_v2",
        "endpoint": "/higgsfield-ai/soul/v2/standard",
        "description": "Commercial-grade photorealistic ad still (Default).",
        "default_params": {
            "aspect_ratio": "1:1",
            "quality": "high",
        }
    },
    "cinematic_ad": {
        "label": "Cinematic Ad",
        "category": "image",
        "model_id": "soul_cinema",
        "endpoint": "/higgsfield-ai/soul-cinema/v1/standard",
        "description": "Luxury, dramatic lighting and editorial depth of field.",
        "default_params": {
            "aspect_ratio": "16:9",
            "quality": "ultra",
        }
    },
    "storyboard": {
        "label": "Storyboard",
        "category": "image",
        "model_id": "popcorn_auto_batch",
        "endpoint": "/higgsfield-ai/popcorn/v1/auto",
        "description": "Multi-angle character & product sequence.",
        "default_params": {
            "aspect_ratio": "1:1",
            "batch_size": 4,
        }
    },
    
    # --- VIDEO MODES ---
    "quick_video": {
        "label": "Quick Video",
        "category": "video",
        "model_id": "dop_turbo",
        "endpoint": "/higgsfield-ai/dop/v1/turbo",
        "description": "Fast motion video for rapid social testing (Default).",
        "default_params": {
            "aspect_ratio": "9:16",
            "duration": 5,
        }
    },
    "premium_video": {
        "label": "Premium Video",
        "category": "video",
        "model_id": "dop_standard",
        "endpoint": "/higgsfield-ai/dop/v1/standard",
        "description": "High fidelity commercial video ad.",
        "default_params": {
            "aspect_ratio": "9:16",
            "duration": 5,
        }
    },
    "before_after": {
        "label": "Before → After",
        "category": "video",
        "model_id": "dop_turbo_flf",
        "endpoint": "/higgsfield-ai/dop/v1/turbo/first-last-frame",
        "description": "Seamless transition from starting state to final result.",
        "default_params": {
            "aspect_ratio": "9:16",
            "duration": 5,
        },
        "requires_inputs": ["start_image_url", "end_image_url"]
    },
    "controlled_video": {
        "label": "Controlled Video",
        "category": "video",
        "model_id": "dop_standard_flf",
        "endpoint": "/higgsfield-ai/dop/v1/standard/first-last-frame",
        "description": "Start and end frame keyframing for strict brand guidelines.",
        "default_params": {
            "aspect_ratio": "9:16",
            "duration": 5,
        },
        "requires_inputs": ["start_image_url", "end_image_url"]
    }
}

DEFAULT_MODE = "premium_ad"

def resolve_mode_spec(mode: Optional[str] = None) -> Dict[str, Any]:
    """Resolves mode configuration or defaults to premium_ad."""
    if not mode or mode not in MODEL_REGISTRY:
        # Check if legacy key was passed
        if mode in ("IMAGE_FAST", "image", "soul_v2", "soul"):
            return MODEL_REGISTRY["premium_ad"]
        elif mode in ("VIDEO_STANDARD", "video", "dop_turbo"):
            return MODEL_REGISTRY["quick_video"]
        return MODEL_REGISTRY[DEFAULT_MODE]
    return MODEL_REGISTRY[mode]

def resolve_endpoint_url(mode_spec: Dict[str, Any]) -> str:
    """Builds the absolute API URL from a mode specification."""
    endpoint_path = mode_spec.get("endpoint", "/higgsfield-ai/soul/v2/standard")
    return f"{HF_API_BASE}{endpoint_path}"
