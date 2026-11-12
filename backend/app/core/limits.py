"""In-process sliding-window limits keyed by account, email or a global name.

The IP limits in ``app.middleware.rate_limit`` depend on knowing the client
address, which a proxy setup can get wrong. These keys come from data the
caller cannot rotate for free: the signed-in account, the email being signed
up / reset / signed in, or one global counter per route. They hold even when
every request arrives with a different forged IP.

Why in process and not Postgres: Helix runs one Render free instance, so one
process sees every request. Counting here adds no database write to every auth
request and keeps working when the database is slow. The cost is that counters
reset on a restart; that is acceptable for abuse throttling. Money is guarded
separately and durably: Metapi record caps live in Postgres
(``app.services.provider_budget``) and survive restarts.

``enforce`` raises 429 with ``Retry-After`` and code ``rate_limited``.
"""
from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import HTTPException, status

_HITS: Dict[str, Deque[float]] = defaultdict(deque)
_MAX_KEYS = 20000


def reset() -> None:
    _HITS.clear()


def _key(bucket: str, subject: str) -> str:
    # Emails are hashed so the table never holds them in clear text.
    digest = hashlib.sha256(subject.strip().lower().encode()).hexdigest()[:32]
    return f"{bucket}:{digest}"


def hit(bucket: str, subject: str, limit: int, window_s: int) -> Optional[int]:
    """Count one hit; return seconds to wait when over ``limit``, else None."""
    if limit <= 0:
        return max(1, int(window_s))
    now = time.monotonic()
    hits = _HITS[_key(bucket, subject)]
    while hits and now - hits[0] > window_s:
        hits.popleft()
    if len(hits) >= limit:
        return int(window_s - (now - hits[0])) + 1
    hits.append(now)
    if len(_HITS) > _MAX_KEYS:
        for k in [k for k, v in _HITS.items() if not v or now - v[-1] > 3600]:
            _HITS.pop(k, None)
    return None


def enforce(bucket: str, subject: str, limit: int, window_s: int, message: str | None = None) -> None:
    retry_after = hit(bucket, subject, limit, window_s)
    if retry_after is None:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "rate_limited",
            "message": message or "Too many requests. Please wait and try again.",
            "retry_after_s": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
