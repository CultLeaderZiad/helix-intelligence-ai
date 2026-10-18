"""Decode and re-encode avatar uploads as a permitted raster image."""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

MAX_AVATAR_BYTES = 2 * 1024 * 1024

_FORMATS = {
    "PNG": ("image/png", "png", "PNG"),
    "JPEG": ("image/jpeg", "jpg", "JPEG"),
    "WEBP": ("image/webp", "webp", "WEBP"),
    "GIF": ("image/gif", "gif", "GIF"),
}


class AvatarRejected(ValueError):
    """The upload is not a small PNG, JPEG, WEBP, or GIF."""


def _looks_like_active_content(data: bytes) -> bool:
    sniff = data[:512].lstrip().lower()
    return (
        sniff.startswith(b"<svg")
        or sniff.startswith(b"<?xml")
        or sniff.startswith(b"<html")
        or sniff.startswith(b"<!doctype")
        or sniff.startswith(b"<script")
        or b"<svg" in sniff
        or b"<script" in sniff
    )


def prepare_avatar_image(data: bytes, max_bytes: int = MAX_AVATAR_BYTES) -> tuple[bytes, str, str]:
    """Return re-encoded bytes, MIME type, and file extension.

    The extension and MIME come from the decoded image, not the client filename.
    Re-encoding drops embedded markup that a browser could treat as active content.
    """
    if not data:
        raise AvatarRejected("Avatar file is empty")
    if len(data) > max_bytes:
        raise AvatarRejected(f"Avatar exceeds the {max_bytes} byte limit")
    if _looks_like_active_content(data):
        raise AvatarRejected("Avatar must be a PNG, JPEG, WEBP, or GIF image")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            fmt = (image.format or "").upper()
            spec = _FORMATS.get(fmt)
            if spec is None:
                raise AvatarRejected("Avatar must be a PNG, JPEG, WEBP, or GIF image")
            mime, ext, save_format = spec
            if save_format == "JPEG" and image.mode != "RGB":
                image = image.convert("RGB")
            elif save_format == "PNG" and image.mode not in {"RGB", "RGBA", "L", "P"}:
                image = image.convert("RGBA")
            out = io.BytesIO()
            if save_format == "JPEG":
                image.save(out, format="JPEG", quality=90)
            elif save_format == "GIF":
                image.save(out, format="GIF")
            elif save_format == "WEBP":
                image.save(out, format="WEBP")
            else:
                image.save(out, format="PNG")
    except AvatarRejected:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AvatarRejected("Avatar must be a PNG, JPEG, WEBP, or GIF image") from exc
    encoded = out.getvalue()
    if not encoded or len(encoded) > max_bytes or _looks_like_active_content(encoded):
        raise AvatarRejected("Avatar must be a PNG, JPEG, WEBP, or GIF image")
    return encoded, mime, ext
