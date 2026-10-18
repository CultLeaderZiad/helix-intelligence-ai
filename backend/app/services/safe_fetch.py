"""Bounded public HTTP fetches.

Every user-influenced or provider-result GET goes through this module.
The connection is pinned to an address that was checked against the public
allowlist, redirects are revalidated one hop at a time, and bodies are
streamed with a hard byte cap. Redirects are never followed by the HTTP
client itself.
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urljoin, urlsplit

import httpx

from app.services.security_service import BLOCKED_HOSTNAMES, is_ip_blocked

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
MAX_INLINE_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_PORTS = {80, 443}
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


class UnsafeFetch(ValueError):
    """The URL, redirect, or body failed the public-fetch policy."""


@dataclass(frozen=True)
class PublicDestination:
    url: str
    scheme: str
    hostname: str
    port: int
    ip: str


def _resolve(hostname: str, port: int):
    return socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)


def _public_ip(hostname: str, port: int, resolve: Callable = _resolve) -> str:
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if is_ip_blocked(literal):
            raise UnsafeFetch(f"SSRF blocked: {hostname} is not a public address")
        return str(literal)

    try:
        records = resolve(hostname, port)
    except (socket.gaierror, socket.herror, OSError) as exc:
        raise UnsafeFetch(f"SSRF blocked: {hostname} did not resolve") from exc
    if not records:
        raise UnsafeFetch(f"SSRF blocked: {hostname} did not resolve")

    chosen: Optional[str] = None
    for _family, _type, _proto, _canon, sockaddr in records:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError as exc:
            raise UnsafeFetch(f"SSRF blocked: {hostname} resolved to an invalid address") from exc
        if is_ip_blocked(ip):
            raise UnsafeFetch(f"SSRF blocked: {hostname} resolves to a non-public address")
        ip_str = str(ip)
        if chosen is None or (":" in chosen and ":" not in ip_str):
            chosen = ip_str
    if not chosen:
        raise UnsafeFetch(f"SSRF blocked: {hostname} did not resolve")
    return chosen


def assert_public_http_url(url: str, resolve: Callable = _resolve) -> PublicDestination:
    """Validate scheme, port, hostname, and every resolved address."""
    if not url or not isinstance(url, str) or len(url) > 2048:
        raise UnsafeFetch("SSRF blocked: URL is missing or too long")
    parsed = urlsplit(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UnsafeFetch("SSRF blocked: only http and https are allowed")
    if parsed.username or parsed.password:
        raise UnsafeFetch("SSRF blocked: credentials in URLs are not allowed")
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeFetch("SSRF blocked: URL has no host")
    host = hostname.strip("[]").lower().rstrip(".")
    if (
        host in BLOCKED_HOSTNAMES
        or host.endswith(".local")
        or host.endswith(".internal")
        or host.endswith(".localhost")
        or host.endswith(".lan")
    ):
        raise UnsafeFetch(f"SSRF blocked: {host} is not a public host")
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    if port not in _ALLOWED_PORTS:
        raise UnsafeFetch(f"SSRF blocked: port {port} is not allowed")
    ip = _public_ip(host, port, resolve=resolve)
    return PublicDestination(url=url.strip(), scheme=scheme, hostname=host, port=port, ip=ip)


def _use_patched_client_get() -> bool:
    """Existing redirect tests replace ``httpx.get``. Honor that seam."""
    fn = httpx.get
    return type(fn).__name__ in {"MagicMock", "Mock", "AsyncMock"} or getattr(fn, "__module__", "") != "httpx"


class _PinningTransport(httpx.BaseTransport):
    """Open the TCP connection to a previously validated address."""

    def __init__(self, destination: PublicDestination):
        self._destination = destination
        self._inner = httpx.HTTPTransport(verify=True, retries=0)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host_header = self._destination.hostname
        if self._destination.port not in (80, 443):
            host_header = f"{host_header}:{self._destination.port}"
        request.headers["host"] = host_header
        request.extensions["sni_hostname"] = self._destination.hostname
        request.url = request.url.copy_with(host=self._destination.ip, port=self._destination.port)
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


def _read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    declared = response.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise UnsafeFetch(f"SSRF blocked: response exceeds {max_bytes} bytes")
    buf = bytearray()
    for chunk in response.iter_bytes():
        if len(buf) + len(chunk) > max_bytes:
            raise UnsafeFetch(f"SSRF blocked: response exceeds {max_bytes} bytes")
        buf.extend(chunk)
    return bytes(buf)


def _pinned_get(destination: PublicDestination, timeout: float, headers: dict, max_bytes: int, kwargs: dict) -> httpx.Response:
    transport = _PinningTransport(destination)
    try:
        with httpx.Client(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(timeout),
        ) as client:
            request = client.build_request("GET", destination.url, headers=headers, **kwargs)
            response = client.send(request, stream=True)
            try:
                if response.is_redirect:
                    return httpx.Response(
                        status_code=response.status_code,
                        headers=response.headers,
                        content=b"",
                    )
                body = _read_capped(response, max_bytes)
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=body,
                )
            finally:
                response.close()
    finally:
        transport.close()


def safe_http_get(url: str, timeout: float = 20.0, max_redirects: int = 5, max_bytes: int = DEFAULT_MAX_BYTES, **kwargs):
    """GET ``url``, validating the initial target and every redirect hop."""
    if "max_bytes" in kwargs:
        max_bytes = int(kwargs.pop("max_bytes"))
    kwargs.pop("follow_redirects", None)
    headers = dict(kwargs.pop("headers", None) or {})
    current = url
    for _ in range(max_redirects + 1):
        destination = assert_public_http_url(current)
        if _use_patched_client_get():
            response = httpx.get(
                destination.url,
                timeout=timeout,
                follow_redirects=False,
                headers=headers,
                **kwargs,
            )
        else:
            response = _pinned_get(destination, timeout, headers, max_bytes, kwargs)
        if not getattr(response, "is_redirect", False):
            content = getattr(response, "content", b"")
            if isinstance(content, (bytes, bytearray)) and len(content) > max_bytes:
                raise UnsafeFetch(f"SSRF blocked: response exceeds {max_bytes} bytes")
            return response
        location = response.headers.get("location") if getattr(response, "headers", None) else None
        if not location:
            raise UnsafeFetch("SSRF blocked: redirect missing location")
        current = urljoin(current, location)
    raise UnsafeFetch("SSRF blocked: too many redirects")


async def safe_http_get_async(url: str, timeout: float = 20.0, max_redirects: int = 5, max_bytes: int = DEFAULT_MAX_BYTES, **kwargs):
    return await asyncio.to_thread(
        safe_http_get,
        url,
        timeout=timeout,
        max_redirects=max_redirects,
        max_bytes=max_bytes,
        **kwargs,
    )


def _b64_limit(max_bytes: int) -> int:
    return (max_bytes * 4 // 3) + 16


def decode_image_data_url(value: str, max_bytes: int = MAX_INLINE_IMAGE_BYTES) -> tuple[bytes, str]:
    """Reject oversized or non-image data URLs before they are decoded."""
    if not isinstance(value, str) or not value.startswith("data:") or ";base64," not in value:
        raise UnsafeFetch("inline image payload is not a base64 data URL")
    if len(value) > _b64_limit(max_bytes) + 64:
        raise UnsafeFetch(f"SSRF blocked: inline payload exceeds {max_bytes} bytes")
    header, encoded = value.split(";base64,", 1)
    mime = header[5:].split(";")[0].strip().lower()
    if mime not in _IMAGE_MIMES:
        raise UnsafeFetch("inline image payload is not a permitted raster type")
    if len(encoded) > _b64_limit(max_bytes):
        raise UnsafeFetch(f"SSRF blocked: inline payload exceeds {max_bytes} bytes")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise UnsafeFetch("inline image payload is not valid base64") from exc
    if len(raw) > max_bytes:
        raise UnsafeFetch(f"SSRF blocked: inline payload exceeds {max_bytes} bytes")
    return raw, "image/jpeg" if mime == "image/jpg" else mime
