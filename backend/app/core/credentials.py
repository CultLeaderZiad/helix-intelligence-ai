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
    # 1. Exact match pass
    for name in names:
        raw = os.environ.get(name)
        if raw is not None:
            value = raw.strip().strip('"\'').strip()
            if value:
                return value

    # 2. Case-insensitive & normalized alias scan
    targets = set()
    for n in names:
        clean_n = n.lower().replace("_", "").replace("-", "")
        targets.add(clean_n)
        for suffix in ("apikey", "key", "token", "secret", "api"):
            if clean_n.endswith(suffix):
                base = clean_n[:-len(suffix)]
                if base:
                    targets.add(base)
        if "metapi" in clean_n:
            targets.add(clean_n.replace("metapi", "metaapi"))
            targets.add("metaapi")

    for k, v in os.environ.items():
        clean_k = k.lower().replace("_", "").replace("-", "")
        if clean_k in targets:
            value = str(v).strip().strip('"\'').strip()
            if value:
                return value


    if fallback is None:
        return ""
    return str(fallback).strip().strip('"\'').strip()
