"""Durable media storage.

Generated media used to be written to a local ``uploads/`` directory. Render's
filesystem is ephemeral, so every restart or deploy destroyed customer media
while the database kept pointing at a URL that now 404s.

When R2 is configured (see ``R2_*`` in ``app.core.config``) media is written to
Cloudflare R2 over the S3-compatible API and survives restarts. When it is not
configured we fall back to the local disk so local development still works --
that fallback is explicitly not durable and says so in the logs.

The public interface (``store_media_bytes`` / ``store_media_from_url``) is
unchanged, so callers such as ``media_service`` do
not need to know which backend is active.
"""

import asyncio
import hashlib
import hmac
import logging
import mimetypes
import os
import time
import uuid
from functools import lru_cache
from typing import Optional
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)

# Local fallback location, used only when R2 is not configured.
# WARNING: on Render this is wiped on restart/deploy.
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


_SAFE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def media_response_headers(filename: str) -> tuple[str, dict]:
    """Restrictive headers for locally served bytes. R2 is the isolated origin when configured."""
    ext = os.path.splitext(filename or "")[1].lower()
    media_type = _SAFE_MEDIA_TYPES.get(ext, "application/octet-stream")
    disposition = "inline" if media_type != "application/octet-stream" else "attachment"
    safe_name = os.path.basename(filename).replace('"', "")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Resource-Policy": "cross-origin",
        "Content-Disposition": f'{disposition}; filename="{safe_name}"',
    }
    return media_type, headers


def _extension_for(mime_type: str) -> str:
    base = (mime_type or "").split(";")[0].strip().lower()
    if base in _EXT_BY_MIME:
        return _EXT_BY_MIME[base]
    guessed = mimetypes.guess_extension(base) if base else None
    return guessed or ".bin"


def is_production() -> bool:
    env = (os.environ.get("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "") or "").lower()
    return env in ("production", "prod") or bool(os.environ.get("RENDER"))


def r2_enabled() -> bool:
    """R2 is used only when it is completely configured.

    ``R2_PUBLIC_BASE_URL`` is part of that requirement on purpose: without a
    public origin the only way to hand out a link is a presigned URL, which
    expires after at most seven days. Storing an expiring URL in the database
    would reintroduce the exact bug this module exists to fix, so a partial
    configuration or running in production without R2 raises a RuntimeError (F49).
    """
    required = (
        settings.R2_ACCOUNT_ID,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET,
        settings.R2_PUBLIC_BASE_URL,
    )
    if all(required):
        return True

    if any(required):
        msg = (
            "R2 is partially configured and therefore invalid. "
            "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
            "R2_BUCKET and R2_PUBLIC_BASE_URL together."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    if is_production():
        msg = "R2 durable storage is required in production environments to prevent media loss."
        logger.error(msg)
        raise RuntimeError(msg)

    return False


@lru_cache(maxsize=1)
def _r2_client():
    import boto3  # imported lazily so the app still boots without boto3
    from botocore.config import Config

    endpoint = (
        settings.R2_ENDPOINT_URL
        or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _r2_put(key: str, data: bytes, mime_type: str, content_disposition: Optional[str] = None) -> None:
    extra = {}
    if content_disposition:
        extra["ContentDisposition"] = content_disposition
    _r2_client().put_object(
        Bucket=settings.R2_BUCKET,
        Key=key,
        Body=data,
        ContentType=mime_type or "application/octet-stream",
        # Media is immutable: the key contains a fresh random component on
        # every write, so it can be cached indefinitely.
        CacheControl="private, max-age=0, no-store",
        **extra,
    )


# ---------------------------------------------------------------------------
# Local fallback signing
#
# Local files are served by app.api.routers.uploads, which requires either a
# valid signature or an authenticated owner. The signature makes the URL a
# capability (the same model as an S3 presigned URL) so an <img> tag works
# without an Authorization header, while an unguessable name plus a keyed MAC
# removes the "predictable filename, no owner check" hole.
# ---------------------------------------------------------------------------

# Short-lived capability. Full JWTs are not accepted as query parameters.
CAPABILITY_TTL_SECONDS = 900


def sign_capability(
    filename: str,
    exp: int,
    org_id: str = "",
    user_id: str = "",
    token_version: str = "",
) -> str:
    message = f"{filename}|{int(exp)}|{org_id}|{user_id}|{token_version}"
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def sign_local_filename(filename: str) -> str:
    """Mac fragment for a default-lifetime capability. Not a permanent signature."""
    return sign_capability(filename, int(time.time()) + CAPABILITY_TTL_SECONDS)


def verify_local_signature(filename: str, signature: Optional[str]) -> bool:
    """Permanent filename-only signatures are rejected."""
    del filename, signature
    return False


def verify_capability(
    filename: str,
    signature: Optional[str],
    exp: Optional[str],
    org_id: str = "",
    user_id: str = "",
    token_version: str = "",
) -> bool:
    if not signature or exp is None or exp == "":
        return False
    try:
        expires = int(exp)
    except (TypeError, ValueError):
        return False
    if expires < int(time.time()):
        return False
    expected = sign_capability(filename, expires, org_id or "", user_id or "", str(token_version or ""))
    return hmac.compare_digest(expected, signature)


def issue_local_url(
    filename: str,
    *,
    org_id: str = "",
    user_id: str = "",
    token_version: str = "",
    ttl_seconds: int = CAPABILITY_TTL_SECONDS,
) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    signature = sign_capability(filename, exp, org_id or "", user_id or "", str(token_version or ""))
    query = (
        f"exp={exp}&org={quote(org_id or '')}&uid={quote(user_id or '')}"
        f"&ver={quote(str(token_version or ''))}&sig={signature}"
    )
    return f"{_public_api_origin()}/uploads/{filename}?{query}"


def _presign_r2_key(key: str, ttl_seconds: int = CAPABILITY_TTL_SECONDS) -> str:
    if not r2_enabled():
        raise RuntimeError("R2 is not configured")
    return _r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET, "Key": key},
        ExpiresIn=int(ttl_seconds),
    )


def resolve_stored_url(
    url: Optional[str],
    *,
    org_id: str = "",
    user_id: str = "",
    token_version: str = "",
    ttl_seconds: int = CAPABILITY_TTL_SECONDS,
) -> Optional[str]:
    """Turn a stored reference into a short-lived URL after the caller is authorized."""
    if not url:
        return url
    if url.startswith("r2://"):
        return _presign_r2_key(url[len("r2://"):], ttl_seconds)
    public = (settings.R2_PUBLIC_BASE_URL or "").rstrip("/")
    if public and (url == public or url.startswith(public + "/")):
        key = url[len(public):].lstrip("/")
        return _presign_r2_key(key, ttl_seconds)
    marker = "/uploads/"
    if marker in url:
        filename = url.split(marker, 1)[1].split("?", 1)[0]
        return issue_local_url(
            filename,
            org_id=org_id,
            user_id=user_id,
            token_version=token_version,
            ttl_seconds=ttl_seconds,
        )
    return url


def _public_api_origin() -> str:
    origin = (
        os.environ.get("PUBLIC_API_BASE_URL")
        or getattr(settings, "PUBLIC_API_BASE_URL", "")
        or os.environ.get("VITE_API_BASE_URL", "http://localhost:8000/api")
    )
    return origin.rstrip("/").removesuffix("/api")


def _store_local(filename: str, data: bytes) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(data)
    logger.warning(
        "Stored %s on EPHEMERAL local disk because R2 is not configured. "
        "This file will be lost on the next restart or deploy.",
        filename,
    )
    return issue_local_url(filename)


async def store_media_bytes(job_id: str, data: bytes, mime_type: str = "image/png") -> str:
    """Persist binary media and return a durable public URL."""
    if not data:
        raise ValueError("store_media_bytes called with empty data")

    ext = _extension_for(mime_type)
    # 128 bits of randomness: the object name is never guessable, whichever
    # backend ends up serving it.
    filename = f"{job_id}_{uuid.uuid4().hex}{ext}"

    if r2_enabled():
        key = f"media/{filename}"
        await asyncio.to_thread(_r2_put, key, data, mime_type)
        logger.info("Stored media for job %s in private R2: %s", job_id, key)
        return f"r2://{key}"

    return _store_local(filename, data)


async def store_media_from_url(job_id: str, source_url: str) -> str:
    """Download provider media and re-host it durably.

    Returns the original URL on failure so the caller never loses the only
    reference it has to the asset.
    """
    try:
        logger.info("Downloading media for job %s from %s", job_id, source_url)
        from app.services.safe_fetch import UnsafeFetch, safe_http_get_async

        response = await safe_http_get_async(source_url, timeout=60.0, max_bytes=50 * 1024 * 1024)
        if response.status_code >= 400:
            raise RuntimeError(f"provider media download returned {response.status_code}")
        content_type = response.headers.get("content-type", "")
        return await store_media_bytes(job_id, response.content, content_type)
    except UnsafeFetch:
        logger.error("Refused to download media for job %s from a non-public URL", job_id)
        raise
    except Exception as e:
        logger.error("Failed to download/store media for job %s: %s", job_id, e)
        return source_url


async def save_file(data: bytes, filename: str, content_type: Optional[str] = None) -> str:
    """Save raw file bytes and return a durable URL (F34).
    
    Compatible with existing callers expecting a filename-based save.
    """
    if not data:
        raise ValueError("save_file called with empty data")

    mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    ext = os.path.splitext(filename)[1] or _extension_for(mime)
    stem = os.path.splitext(filename)[0].replace("/", "_").replace("\\", "_")
    unique_filename = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"

    if r2_enabled():
        key = f"uploads/{unique_filename}"
        await asyncio.to_thread(_r2_put, key, data, mime, f'inline; filename="{unique_filename}"')
        logger.info("Saved file in private R2: %s", key)
        return _presign_r2_key(key)

    return _store_local(unique_filename, data)


async def save_avatar(data: bytes, mime_type: str, extension: str, user_id: str) -> str:
    """Store a re-encoded avatar. R2 is a separate media origin when configured."""
    if not data:
        raise ValueError("save_avatar called with empty data")
    filename = f"avatar_{user_id}_{uuid.uuid4().hex[:12]}.{extension}"
    disposition = f'inline; filename="avatar.{extension}"'
    if r2_enabled():
        key = f"avatars/{filename}"
        await asyncio.to_thread(_r2_put, key, data, mime_type, disposition)
        return f"r2://{key}"
    _store_local(filename, data)
    return f"/uploads/{filename}"

