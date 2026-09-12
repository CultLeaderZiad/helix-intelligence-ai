"""Read API credentials at call time.

Pydantic field defaults of ``os.getenv(...)`` are evaluated at import and can
stay empty even after Render injects the real env var into a running process
that was not restarted, or after an empty ``METAPI_API_KEY=`` line in an
env file wins. Providers should call this instead of trusting a cached
Settings value alone.

Process environment wins (what Render injects). Settings / env-file values
are the local-dev fallback.
"""

from __future__ import annotations

import os
from typing import Optional


def env_secret(*names: str, fallback: Optional[str] = None) -> str:
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        value = raw.strip().strip('"').strip("'")
        if value:
            return value
    if fallback is None:
        return ""
    return str(fallback).strip().strip('"').strip("'")
