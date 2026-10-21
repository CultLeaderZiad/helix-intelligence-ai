from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace

import pytest

from app.services import storage_service
from app.api.routers.account import _avatar_url


@pytest.mark.asyncio
async def test_local_avatar_writes_bytes_before_issuing_signed_url(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(storage_service, "r2_enabled", lambda: False)
    monkeypatch.setenv("PUBLIC_API_BASE_URL", "/api")

    reference = await storage_service.save_avatar(b"re-encoded-image", "image/png", "png", "local-user")
    assert reference.startswith("/uploads/") and "?" not in reference
    url = _avatar_url(SimpleNamespace(
        id="local-user", avatar_url=reference, signup_metadata={"token_version": 7},
    ))
    parts = urlsplit(url)
    filename = parts.path.removeprefix("/uploads/")
    query = {key: values[0] for key, values in parse_qs(parts.query, keep_blank_values=True).items()}

    assert not parts.netloc
    assert filename.startswith("avatar_local-user_")
    assert query["uid"] == "local-user" and query["ver"] == "7"
    assert (tmp_path / filename).read_bytes() == b"re-encoded-image"
    assert storage_service.verify_capability(
        filename, query["sig"], query["exp"], query["org"], query["uid"], query["ver"],
    )
