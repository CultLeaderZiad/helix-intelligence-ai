"""Versioned persisted discovery identity, shared by reads and active uniqueness.

Legacy jobs have no identity and are deliberately never reused: their original
filters/provider configuration cannot be reconstructed safely.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

# Bump when search semantics, normalization or provider implementation changes.
DISCOVERY_CACHE_VERSION = "discovery-v1"

# These public multi-select filters are sets, unlike unknown/future arrays
# whose ordering may carry meaning. Keep scalar types and unknown fields intact.
_SET_FILTERS = frozenset({"platforms", "formats", "spend_bands"})


def _canonical_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(filters or {})
    for name in _SET_FILTERS:
        values = normalized.get(name)
        if isinstance(values, list):
            # Sorting serialized values is deterministic even for mixed JSON
            # types; do not coerce strings/numbers/null into the same identity.
            serialized = {json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False)
                          for value in values}
            normalized[name] = [json.loads(value) for value in sorted(serialized)]
    return normalized


def discovery_cache_identity(*, query: str, filters: dict[str, Any] | None,
                             org_id: str, provider: str,
                             version: str | None = None) -> str:
    """Hash the complete namespace; object key order is not semantic.

    Sort/deduplicate known multi-select filters; preserve unknown array order
    and scalar types (including null/false) so future filters cannot accidentally
    share cached results. Reject NaN/Inf
    rather than persisting an identity that is not valid JSON.
    """
    normalized_query = " ".join(unicodedata.normalize("NFKC", query).casefold().split())
    canonical = json.dumps({
        "version": DISCOVERY_CACHE_VERSION if version is None else version,
        "org_id": str(org_id),
        "provider": provider,
        "query": normalized_query,
        "filters": _canonical_filters(filters),
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
