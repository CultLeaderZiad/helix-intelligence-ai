"""Small sliding-window throttle for auth-facing endpoints.

Scope — stated plainly, because it is the part that gets people hurt:

* Buckets live in this process. Render runs this service as a single uvicorn
  worker, so today one process == the whole service and the limit is real. If
  the service is ever scaled (``numInstances > 1``, ``--workers > 1``), each
  process keeps its own counters and the effective ceiling multiplies. That is
  why every throttle here is a *soft* limit and the one that actually matters
  for password reset — "don't keep re-minting links for the same address" — is
  enforced in the database (``users.password_reset_expires_at``) and therefore
  survives both workers and restarts.
* Nothing here is durable: a restart clears the counters. A limiter is not an
  audit log and not a lockout policy.

Keys are ``"<bucket>:<identity>"``. Identity is the client network for the
per-IP buckets, which is best effort behind a proxy (see :func:`client_ip`), so
the per-IP buckets are paired with per-address buckets wherever an attacker
could otherwise rotate networks.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Dict, Tuple

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    """Fixed-window-ish limiter: keeps per-key timestamps inside the window."""

    def __init__(self, max_keys: int = 20_000) -> None:
        self._hits: Dict[str, deque] = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def _sweep(self, now: float, window: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window]:
            self._hits.pop(key, None)
        # Still at capacity (hot keys, many distinct IPs): drop a slice of the
        # oldest buckets rather than growing without bound.
        if len(self._hits) >= self._max_keys:
            for key in list(self._hits)[: max(1, self._max_keys // 8)]:
                self._hits.pop(key, None)

    def check(self, key: str, limit: int, window_seconds: float) -> Tuple[bool, float, int]:
        """Consume one attempt. Returns ``(allowed, retry_after_seconds, remaining)``.

        Consumes on entry regardless of the request's outcome: the thing being
        limited is the attempt, not the failure.
        """
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.get(key)
            if bucket is None:
                if len(self._hits) >= self._max_keys:
                    self._sweep(now, window_seconds)
                bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()

            if limit > 0 and len(bucket) >= limit:
                retry_after = max(0.0, bucket[0] + window_seconds - now)
                return False, retry_after, 0

            bucket.append(now)
            return True, 0.0, max(0, limit - len(bucket))

    def clear(self) -> None:
        """Test helper: forget every bucket."""
        with self._lock:
            self._hits.clear()


# One shared limiter for the auth surface; separate `bucket:` prefixes keep the
# counters independent (blasting the forgot-password budget must not silently
# grant unlimited sign-in attempts).
AUTH_LIMITER = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """Best-effort client address.

    Behind Render's proxy ``request.client.host`` is the proxy, so
    ``X-Forwarded-For`` is used — and its leftmost entry is attacker-chosen if
    a caller sends one. That makes this key *soft* by construction: it is fine
    for "don't hammer this from one network" and is never the only thing
    standing between a request and a security decision.
    """
    xff = request.headers.get("x-forwarded-for") or ""
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    forwarded = request.headers.get("forwarded") or ""
    if "for=" in forwarded:
        return forwarded.split("for=", 1)[1].split(";")[0].strip().strip('"') or "unknown"
    return request.client.host if request.client else "unknown"


def throttle(request: Request, bucket: str, limit: int, window_seconds: float, *, message: str) -> int:
    """Raise 429 (with Retry-After) when ``bucket:client_ip`` is over budget.

    Returns the remaining allowance so callers can set the matching header.
    """
    allowed, retry_after, remaining = AUTH_LIMITER.check(
        f"{bucket}:{client_ip(request)}", limit, window_seconds
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"code": "too_many_requests", "message": message},
            headers={
                "Retry-After": str(max(1, int(retry_after) + 1)),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
    return remaining
