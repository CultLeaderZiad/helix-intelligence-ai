"""Durable media storage.

Generated media used to be written to a local ``uploads/`` directory. Render's
filesystem is ephemeral, so every restart or deploy destroyed customer media
while the database kept pointing at a URL that now 404s.

When R2 is configured (see ``R2_*`` in ``app.core.config``) media is written to
Cloudflare R2 over the S3-compatible API and survives restarts. When it is not
configured we fall back to the local disk so local development still works --
that fallback is explicitly not durable and says so in the logs.

The public interface (``store_media_bytes`` / ``store_media_from_url``) is
unchanged, so callers such as ``media_service`` and the Higgsfield webhook do
not need to know which backend is active.
"""

import asyncio
import hashlib
import hmac
import logging
import mimetypes
import os
import uuid
from functools import lru_cache
from typing import Optional

import httpx

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


def _extension_for(mime_type: str) -> str:
    base = (mime_type or "").split(";")[0].strip().lower()
    if base in _EXT_BY_MIME:
        return _EXT_BY_MIME[base]
    guessed = mimetypes.guess_extension(base) if base else None
    return guessed or ".bin"


def r2_enabled() -> bool:
    """R2 is used only when it is completely configured.

    ``R2_PUBLIC_BASE_URL`` is part of that requirement on purpose: without a
    public origin the only way to hand out a link is a presigned URL, which
    expires after at most seven days. Storing an expiring URL in the database
    would reintroduce the exact bug this module exists to fix, so a partial
    configuration falls back to local disk and logs loudly instead.
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
        logger.error(
            "R2 is partially configured and therefore disabled. "
            "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
            "R2_BUCKET and R2_PUBLIC_BASE_URL together. "
            "Falling back to EPHEMERAL local disk."
        )
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


def _r2_put(key: str, data: bytes, mime_type: str) -> None:
    _r2_client().put_object(
        Bucket=settings.R2_BUCKET,
        Key=key,
        Body=data,
        ContentType=mime_type or "application/octet-stream",
        # Media is immutable: the key contains a fresh random component on
        # every write, so it can be cached indefinitely.
        CacheControl="public, max-age=31536000, immutable",
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

def sign_local_filename(filename: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        filename.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]


def verify_local_signature(filename: str, signature: Optional[str]) -> bool:
    if not signature:
        return False
    return hmac.compare_digest(sign_local_filename(filename), signature)


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
    return f"{_public_api_origin()}/uploads/{filename}?sig={sign_local_filename(filename)}"


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
        url = f"{settings.R2_PUBLIC_BASE_URL}/{key}"
        logger.info("Stored media for job %s in R2: %s", job_id, key)
        return url

    return _store_local(filename, data)


async def store_media_from_url(job_id: str, source_url: str) -> str:
    """Download provider media and re-host it durably.

    Returns the original URL on failure so the caller never loses the only
    reference it has to the asset.
    """
    try:
        logger.info("Downloading media for job %s from %s", job_id, source_url)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return await store_media_bytes(job_id, response.content, content_type)
    except Exception as e:
        logger.error("Failed to download/store media for job %s: %s", job_id, e)
        return source_url
