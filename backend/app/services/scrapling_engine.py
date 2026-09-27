"""scrapling_engine - thin wrapper around the Scrapling library.

Engine id: scrapling_engine. Helix never imports Scrapling in the Vite app;
only the worker (or the opt-in inline dev fallback) loads this module, and
Scrapling itself is imported LAZILY inside functions so the FastAPI process
boots without browsers installed.

Capability map (spec section 3):
  Fetcher         -> engine=http      (fast TLS impersonation)
  StealthyFetcher -> engine=stealth   (default; unknown / Cloudflare)
  DynamicFetcher  -> engine=dynamic   (JS-heavy; Playwright)
  ProxyRotator    -> org/job proxy list (first proxy used per request)
  adaptive css    -> recipe selectors via Scrapling Selector(adaptive=True)
  page.markdown   -> digest / markdown artifacts (to_markdown)
  robots_txt_obey -> checked before every fetch (default ON)
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib import robotparser

logger = logging.getLogger(__name__)

ENGINE_VERSION = "v1"
_BLOCK_STATUS = {401, 403, 429, 503}
_CHALLENGE_MARKERS = (
    "cf-chl-", "cloudflare", "captcha", "just a moment", "attention required",
    "ddos protection", "access denied",
)

# robots cache: origin -> RobotFileParser | False (unreachable -> fail open)
_ROBOTS_CACHE: Dict[str, Any] = {}


def is_available() -> bool:
    """True when Scrapling is importable in THIS process (worker/inline only)."""
    import importlib.util
    return importlib.util.find_spec("scrapling") is not None


def engine_header(engine: str) -> str:
    return f"> engine: scrapling/{engine}/{ENGINE_VERSION}"


def robots_allowed(url: str) -> bool:
    """robots.txt gate. Disallow => blocked. If robots.txt is unreachable,
    fall back to allow (standard crawler behavior)."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin in _ROBOTS_CACHE:
        entry = _ROBOTS_CACHE[origin]
        return True if entry is False else bool(entry.can_fetch("*", url))
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{origin}/robots.txt")
    try:
        rp.read()
        _ROBOTS_CACHE[origin] = rp
        return bool(rp.can_fetch("*", url))
    except Exception:
        _ROBOTS_CACHE[origin] = False
        return True


def _first_proxy() -> Optional[str]:
    from app.core.config import settings
    raw = (settings.SCRAPLING_PROXY_LIST or "").strip()
    if not raw:
        return None
    first = re.split(r"[\n,]", raw)[0].strip()
    return first or None


def fetch(
    url: str,
    engine: str = "stealth",
    robots_obey: bool = True,
    capture_xhr_pattern: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Fetch one public URL. Returns
    {fetch_status: ok|blocked|rate_limited|error, status_code, html, url, reason?}.
    Never raises for network outcomes - status is data, not control flow.
    """
    if robots_obey and not robots_allowed(url):
        return {"fetch_status": "blocked", "status_code": 0, "html": None, "url": url, "reason": "robots_disallow"}
    if not is_available():
        return {"fetch_status": "error", "status_code": 0, "html": None, "url": url, "reason": "scrapling_unavailable"}

    from scrapling.fetchers import Fetcher, StealthyFetcher  # lazy import

    proxy = _first_proxy()
    try:
        if engine == "http":
            kwargs: dict = {"timeout": timeout}
            if proxy:
                kwargs["proxy"] = proxy
            resp = Fetcher.get(url, **kwargs)
        elif engine == "dynamic":
            from scrapling.fetchers import DynamicFetcher
            kwargs = {"timeout": timeout, "wait": 3000}
            if proxy:
                kwargs["proxy"] = proxy
            resp = DynamicFetcher.get(url, **kwargs)
        else:  # stealth (default)
            kwargs = {"timeout": timeout}
            if proxy:
                kwargs["proxy"] = proxy
            resp = StealthyFetcher.get(url, **kwargs)
    except Exception as e:
        msg = str(e).lower()
        reason = "timeout" if "timeout" in msg or "timed out" in msg else str(e)[:300]
        return {"fetch_status": "error", "status_code": 0, "html": None, "url": url, "reason": reason}

    status = int(getattr(resp, "status", 0) or 0)
    html = getattr(resp, "text", None) or getattr(resp, "body", None) or ""
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    final_url = getattr(resp, "url", url) or url

    if status == 429:
        return {"fetch_status": "rate_limited", "status_code": status, "html": None, "url": final_url}
    if status in _BLOCK_STATUS:
        head = html[:2000].lower() if html else ""
        if any(m in head for m in _CHALLENGE_MARKERS) or status in (403, 503):
            return {"fetch_status": "blocked", "status_code": status, "html": None, "url": final_url}
        return {"fetch_status": "error", "status_code": status, "html": None, "url": final_url}
    if status >= 500 or status == 0:
        return {"fetch_status": "error", "status_code": status, "html": None, "url": final_url}

    return {"fetch_status": "ok", "status_code": status, "html": html, "url": final_url}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s\-()]{7,16}\d)(?!\d)")
_SOCIAL_HOSTS = ("instagram.com", "x.com", "twitter.com", "linkedin.com", "facebook.com", "tiktok.com", "youtube.com")
_SKIP_EMAILS = {"user@example.com", "email@example.com", "name@example.com"}


def extract_contacts(html: str, selectors: Optional[dict] = None, url: str = "") -> Dict[str, Any]:
    """Extract public contact fields from HTML.

    NEVER invents: missing fields stay empty; extract_status reflects reality.
    Recipe selectors first (via Scrapling's adaptive Selector when available),
    then universal regex harvesting of mailto:/tel: hrefs + visible text.
    """
    result: Dict[str, Any] = {
        "company_name": None,
        "emails": [],
        "phones": [],
        "socials": {},
        "address": None,
        "selector_hits": {},
        "adaptive_used": False,
    }
    if not html:
        return result

    selectors = selectors or {}
    dom = None
    if is_available():
        try:
            from scrapling.parser import Selector
            kwargs = {"url": url} if url else {}
            if selectors.get("_adaptive"):
                kwargs["adaptive"] = True
            dom = Selector(html, **kwargs)
            result["adaptive_used"] = bool(selectors.get("_adaptive"))
        except Exception:
            dom = None

    # 1) Recipe selectors (adaptive CSS via Scrapling's selector engine)
    for field in ("company_name", "emails", "phones", "address"):
        spec = selectors.get(field)
        if not isinstance(spec, dict) or not spec.get("css") or dom is None:
            continue
        try:
            nodes = dom.css(spec["css"])
            values = []
            for n in nodes[:20]:
                raw = ""
                if spec.get("attr"):
                    try:
                        raw = n.attrib.get(spec["attr"], "")
                    except Exception:
                        raw = ""
                if not raw:
                    raw = getattr(n, "text", "") or ""
                raw = (raw or "").strip()
                if raw:
                    values.append(raw)
            if values:
                result["selector_hits"][field] = len(values)
                if field == "company_name":
                    result["company_name"] = values[0][:200]
                elif field == "address":
                    result["address"] = values[0][:500]
                else:
                    result[field].extend(values)
        except Exception as e:
            logger.debug("selector failed for %s: %s", field, e)

    # 2) Universal regex harvesting (mailto: / tel: hrefs + visible text)
    for e in _EMAIL_RE.findall(html):
        e = e.lower()
        if e not in _SKIP_EMAILS and e not in result["emails"]:
            result["emails"].append(e)
    for p in _PHONE_RE.findall(html):
        p = p.strip()
        digits = re.sub(r"\D", "", p)
        if 8 <= len(digits) <= 15 and p not in result["phones"]:
            result["phones"].append(p)

    # 3) Social links
    for host in _SOCIAL_HOSTS:
        m = re.search(rf"https?://(?:www\.)?{re.escape(host)}/[A-Za-z0-9_.\-/]+", html)
        if m:
            result["socials"][host.split(".")[0]] = m.group(0).rstrip("/")[:300]

    # 4) Company name fallback: og:site_name or first <h1>
    if not result["company_name"]:
        m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', html, re.I) or \
            re.search(r"<h1[^>]*>([^<]{2,120})</h1>", html, re.I)
        if m:
            result["company_name"] = m.group(1).strip()[:200]

    # 5) Address fallback: <address> block
    if not result["address"]:
        m = re.search(r"<address[^>]*>(.*?)</address>", html, re.I | re.S)
        if m:
            result["address"] = re.sub(r"<[^>]+>", " ", m.group(1)).strip()[:500]

    result["emails"] = result["emails"][:10]
    result["phones"] = result["phones"][:10]
    return result


def to_markdown(html: str, url: str = "", max_chars: int = 4000) -> Optional[str]:
    """Best-effort markdown digest of a page. Used for digest/crawl markdown
    artifacts. Returns None on failure - never fakes content."""
    if not html:
        return None
    try:
        import html as _html
        text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
        text = re.sub(
            r"(?i)<h([1-3])[^>]*>(.*?)</h\1>",
            lambda m: "\n\n" + "#" * int(m.group(1)) + " " + re.sub(r"<[^>]+>", "", m.group(2)).strip() + "\n",
            text,
        )
        text = re.sub(r"(?i)<li[^>]*>(.*?)</li>", lambda m: "- " + re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n", text)
        text = re.sub(
            r"(?i)<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            lambda m: f"{re.sub(r'<[^>]+>', '', m.group(2)).strip()} ({m.group(1)})",
            text,
        )
        text = re.sub(r"(?i)<(p|br|div|tr)[^>]*>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = _html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception:
        return None
    return text[:max_chars] if text else None
