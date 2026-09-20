"""
Scout scraper utilities
Adapted from kiryano/Scout (MIT) for Helix Intelligence
"""
import re
from typing import List, Optional

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE
)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}", re.IGNORECASE
)

# Avoid static asset false positives
EMAIL_EXCLUDES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".js", ".css", "example.com", "domain.com")


def extract_emails(text: str) -> List[str]:
    """Extract distinct valid emails from string."""
    if not text:
        return []
    found = EMAIL_REGEX.findall(text)
    valid = []
    for email in found:
        e = email.strip().lower().rstrip(".")
        if any(e.endswith(ext) for ext in EMAIL_EXCLUDES):
            continue
        if "@" in e and "." in e.split("@")[-1] and e not in valid:
            valid.append(e)
    return valid


def extract_phones(text: str) -> List[str]:
    """Extract distinct phone numbers from string."""
    if not text:
        return []
    found = PHONE_REGEX.findall(text)
    valid = []
    for ph in found:
        cleaned = re.sub(r"[^\d+]", "", ph)
        if 8 <= len(cleaned) <= 16 and cleaned not in valid:
            valid.append(ph.strip())
    return valid


def clean_handle(handle: str) -> str:
    """Strip leading @ and protocol from handle."""
    if not handle:
        return ""
    h = handle.strip().lstrip("@")
    h = re.sub(r"^https?://[^/]+/", "", h)
    return h.split("?")[0].split("#")[0].strip("/")
