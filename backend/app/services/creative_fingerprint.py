"""Deciding whether two scraped ads are "the same ad" seen twice.

None of the ad-library providers behind Discover return a stable advertiser ad
ID — ``RawCreative`` has no such field, and the ``brand_id`` stored on a
creative is a fresh UUID minted per job. So identity has to be reconstructed
from the ad's own content, and every rule below is a trade-off rather than a
fact. They are written out explicitly because the diff is only as trustworthy
as these choices.

Two hashes per creative:

``identity``
    What makes this "the same ad" across runs. Anchored on the headline, which
    is the most distinctive human-visible part of an ad and the part an
    advertiser is least likely to edit in place.

``content``
    What the ad currently says. Compared against the stored identity to detect
    an edit.

The split is what makes ``copy_changed`` possible at all: if body and CTA were
part of identity, an edited ad would look like one ad dying and another being
born.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import hashlib
import re
import unicodedata

# Bumped if the hashing rules below change in a way that would otherwise make
# already-stored fingerprints silently incomparable with newly computed ones.
FINGERPRINT_VERSION = "v1"

# How many consecutive runs an ad must be absent before it is called dead.
# One absence is far more often a partial scrape than a paused ad.
DEFAULT_MISS_THRESHOLD = 2

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
# Ad libraries hand back copy containing unresolved merge tags. They carry no
# information and their presence should not make two ads look different.
_MERGE_TAG = re.compile(r"\{\{.*?\}\}|\[\[.*?\]\]|%%.*?%%")
_TRACKING_PREFIX = re.compile(r"^(www|m|l|link|go|track|click)\.")


def normalize_text(value: Optional[str]) -> str:
    """Collapse a copy field to its comparable core.

    Case, punctuation, accents and whitespace all vary run to run without the
    ad having changed, so none of them may contribute to a hash.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = _MERGE_TAG.sub(" ", text)
    text = _PUNCTUATION.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


def normalize_domain(value: Optional[str]) -> str:
    if not value:
        return ""
    domain = str(value).strip().casefold()
    domain = domain.split("//")[-1].split("/")[0].split("?")[0]
    return _TRACKING_PREFIX.sub("", domain).strip(".")


def _hash(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:40]


@dataclass(frozen=True)
class CreativeSignature:
    """The two hashes plus enough context to explain them in the UI."""

    identity: str
    content: str
    # 'headline' | 'body' | 'none' — which field anchored identity. A 'none'
    # anchor means the ad had no usable copy and its identity rests only on
    # platform/domain/format, which is weak; the diff treats it accordingly.
    anchor: str
    creative_id: Optional[str] = None
    platform: str = ""
    format: str = ""
    headline: str = ""
    body: str = ""
    cta: str = ""
    landing_domain: str = ""

    @property
    def is_weakly_identified(self) -> bool:
        return self.anchor == "none"


def signature_for(
    *,
    platform: Optional[str],
    format: Optional[str],
    headline: Optional[str],
    body: Optional[str],
    cta: Optional[str],
    landing_domain: Optional[str],
    creative_id: Optional[str] = None,
) -> CreativeSignature:
    """Compute the identity/content pair for a single creative.

    ``format`` is part of identity rather than content: an advertiser turning an
    image ad into a video ad has made a different ad, not edited this one.
    """
    norm_headline = normalize_text(headline)
    norm_body = normalize_text(body)
    norm_cta = normalize_text(cta)
    norm_domain = normalize_domain(landing_domain)
    norm_platform = (platform or "").strip().casefold()
    norm_format = (format or "").strip().casefold()

    if norm_headline:
        anchor, anchor_value = "headline", norm_headline
    elif norm_body:
        # No headline to anchor on. Falling back to the body means an edit to a
        # headline-less ad reads as new+killed rather than copy_changed, which
        # is the honest outcome: there is nothing left to recognise it by.
        anchor, anchor_value = "body", norm_body
    else:
        anchor, anchor_value = "none", ""

    identity = _hash(
        FINGERPRINT_VERSION, "id", norm_platform, norm_domain, norm_format, anchor, anchor_value
    )
    content = _hash(
        FINGERPRINT_VERSION, "content", norm_headline, norm_body, norm_cta
    )

    return CreativeSignature(
        identity=identity,
        content=content,
        anchor=anchor,
        creative_id=creative_id,
        platform=platform or "",
        format=format or "",
        headline=(headline or "").strip(),
        body=(body or "").strip(),
        cta=(cta or "").strip(),
        landing_domain=landing_domain or "",
    )


def signatures_for_run(creatives: Iterable) -> List[CreativeSignature]:
    """Sign every creative in a run, disambiguating genuine duplicates.

    A single query legitimately returns several ads that normalize to the same
    identity — the same copy pointed at the same domain, or several ads with no
    copy at all. They must not collapse into one row, or a run returning three
    copies would look like two ads dying.

    Duplicates are ordered by content hash, which is deterministic, so the same
    set of ads produces the same assignment on every run. The ordering is only
    stable while the duplicate group is; if the number of copies changes, the
    surplus entries churn. That is a known and accepted limit of having no
    provider ad ID, and it is confined to exact duplicates.
    """
    signed = [
        signature_for(
            platform=getattr(c, "platform", None),
            format=getattr(c, "format", None),
            headline=getattr(c, "headline", None),
            body=getattr(c, "body", None),
            cta=getattr(c, "cta", None),
            landing_domain=getattr(c, "landing_domain", None),
            creative_id=getattr(c, "id", None),
        )
        for c in creatives
    ]

    grouped: Dict[str, List[CreativeSignature]] = {}
    for sig in signed:
        grouped.setdefault(sig.identity, []).append(sig)

    result: List[CreativeSignature] = []
    for identity, group in grouped.items():
        if len(group) == 1:
            result.append(group[0])
            continue
        # The first copy keeps the base identity so it stays comparable with
        # previous runs; only the surplus copies get a suffix.
        for index, sig in enumerate(sorted(group, key=lambda s: (s.content, s.creative_id or ""))):
            if index == 0:
                result.append(sig)
            else:
                suffixed = _hash(FINGERPRINT_VERSION, "dup", identity, str(index))
                result.append(CreativeSignature(**{**sig.__dict__, "identity": suffixed}))
    return result


@dataclass
class PriorState:
    """What the monitor already remembers about one identity."""

    identity: str
    content: str
    status: str = "active"
    missed_runs: int = 0


@dataclass
class DiffResult:
    new: List[CreativeSignature]
    changed: List[Tuple[CreativeSignature, PriorState]]
    killed: List[PriorState]
    # Identities absent this run but not yet absent often enough to be called
    # dead. Their miss counters still need persisting.
    pending_misses: List[PriorState]
    # Identities seen again after being absent, so their counter resets.
    recovered: List[PriorState]
    unchanged: int = 0
    skipped_reason: Optional[str] = None

    @property
    def is_skipped(self) -> bool:
        return self.skipped_reason is not None

    @property
    def total_events(self) -> int:
        return len(self.new) + len(self.changed) + len(self.killed)


def diff_run(
    current: Sequence[CreativeSignature],
    previous: Dict[str, PriorState],
    *,
    is_baseline: bool = False,
    miss_threshold: int = DEFAULT_MISS_THRESHOLD,
) -> DiffResult:
    """Compare one run's creatives against what the monitor remembers.

    Two deliberate refusals to report:

    - A baseline run emits nothing. The first time a monitor runs, every ad is
      technically new, and telling the user they have forty new ads is noise,
      not intelligence.
    - A run that returned nothing emits nothing. An empty scrape is
      indistinguishable from a provider outage, and "all your competitor's ads
      were killed" is the single most damaging thing this feature could get
      wrong.
    """
    if not current:
        return DiffResult([], [], [], [], [], 0, skipped_reason="empty_result")

    if is_baseline:
        return DiffResult([], [], [], [], [], len(current), skipped_reason="baseline")

    new: List[CreativeSignature] = []
    changed: List[Tuple[CreativeSignature, PriorState]] = []
    recovered: List[PriorState] = []
    unchanged = 0

    seen_identities = set()
    for sig in current:
        seen_identities.add(sig.identity)
        prior = previous.get(sig.identity)

        if prior is None or prior.status == "gone":
            # A previously dead identity coming back is a relaunch. There is no
            # separate event type for it, and new_ad is the accurate summary:
            # this ad is running now and it was not running before.
            new.append(sig)
            continue

        if prior.content != sig.content:
            changed.append((sig, prior))
        else:
            unchanged += 1

        if prior.missed_runs:
            recovered.append(prior)

    killed: List[PriorState] = []
    pending: List[PriorState] = []
    for identity, prior in previous.items():
        if identity in seen_identities or prior.status != "active":
            continue
        misses = prior.missed_runs + 1
        if misses >= miss_threshold:
            killed.append(prior)
        else:
            pending.append(prior)

    return DiffResult(
        new=new,
        changed=changed,
        killed=killed,
        pending_misses=pending,
        recovered=recovered,
        unchanged=unchanged,
    )
