"""
Scout target parser & validator
Handles URL extraction, handle cleaning, and platform mapping.
"""
import re
from typing import List, Dict, Any, Optional

URL_MAP = [
    (r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]+)", "instagram"),
    (r"(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9._-]+)", "linkedin"),
    (r"(?:https?://)?(?:www\.)?linkedin\.com/company/([A-Za-z0-9._-]+)", "linkedin"),
    (r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9._-]+)", "tiktok"),
    (r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9._-]+)", "github"),
    (r"(?:https?://)?(?:www\.)?linktr\.ee/([A-Za-z0-9._-]+)", "linktree"),
    (r"(?:https?://)?(?:www\.)?youtube\.com/@([A-Za-z0-9._-]+)", "youtube"),
    (r"(?:https?://)?(?:www\.)?youtube\.com/(?:c|channel)/([A-Za-z0-9._-]+)", "youtube"),
    (r"(?:https?://)?(?:www\.)?twitch\.tv/([A-Za-z0-9._-]+)", "twitch"),
    (r"(?:https?://)?(?:www\.)?pinterest\.com/([A-Za-z0-9._-]+)", "pinterest"),
]

BASE_URLS = {
    "instagram": "https://instagram.com/{}",
    "github": "https://github.com/{}",
    "linktree": "https://linktr.ee/{}",
    "tiktok": "https://tiktok.com/@{}",
    "linkedin": "https://linkedin.com/in/{}",
    "youtube": "https://youtube.com/@{}",
    "twitch": "https://twitch.tv/{}",
    "pinterest": "https://pinterest.com/{}",
}


def parse_line(raw: str, default_platform: str = "instagram") -> Dict[str, Any]:
    """
    Parses a single line (URL or raw handle).
    Raises ValueError on invalid formats (e.g. spaces, empty).
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("empty_input")

    # Reject handles containing spaces or tabs (unless full URL)
    if (" " in raw or "\t" in raw) and "://" not in raw:
        raise ValueError(f"invalid_handle_spaces: '{raw}' cannot contain spaces")

    # 1. Test against known URL patterns
    for pattern, platform in URL_MAP:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            handle = match.group(1).strip("/?#").lstrip("@")
            clean_url = BASE_URLS.get(platform, "https://{}").format(handle)
            return {
                "platform": platform,
                "handle": handle,
                "profile_url": clean_url,
                "is_url": True,
            }

    # 2. Bare handle
    handle = raw.lstrip("@").strip()
    # Strip URL fragments if any
    handle = re.sub(r"^https?://[^/]+/", "", handle).split("?")[0].split("#")[0].strip("/")

    if not handle:
        raise ValueError("empty_handle")

    # Reject if spaces remain
    if " " in handle or "\t" in handle:
        raise ValueError(f"invalid_handle_spaces: '{handle}'")

    # Validate handle characters
    if not re.fullmatch(r"[A-Za-z0-9._-]+", handle):
        raise ValueError(f"invalid_handle_characters: '{handle}'")

    clean_url = BASE_URLS.get(default_platform, "https://{}").format(handle)
    return {
        "platform": default_platform,
        "handle": handle,
        "profile_url": clean_url,
        "is_url": False,
    }


def parse_input_targets(lines: List[str], selected_platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Expands input lines into actionable target records.
    If line is a URL: binds to that specific platform.
    If line is a bare handle: generates a target for each selected platform (or default platform).
    """
    platforms = [p.lower() for p in (selected_platforms or ["instagram"])]
    if not platforms:
        platforms = ["instagram"]

    targets: List[Dict[str, Any]] = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            parsed = parse_line(line, default_platform=platforms[0])
            if parsed["is_url"]:
                key = (parsed["platform"], parsed["handle"].lower())
                if key not in seen:
                    seen.add(key)
                    targets.append(parsed)
            else:
                # Handle applies across selected platforms
                for p in platforms:
                    key = (p, parsed["handle"].lower())
                    if key not in seen:
                        seen.add(key)
                        url = BASE_URLS.get(p, "https://{}").format(parsed["handle"])
                        targets.append({
                            "platform": p,
                            "handle": parsed["handle"],
                            "profile_url": url,
                            "is_url": False,
                        })
        except ValueError as e:
            # Re-raise to let caller return clean 400
            raise e

    return targets
