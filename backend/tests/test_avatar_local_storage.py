from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace

import pytest

from app.services import storage_service
from app.api.routers.account import _acceptable_avatar_reference, _avatar_url


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
    assert storage_service.is_user_avatar_filename(filename, "local-user")
    assert "local-user" not in filename
    assert query["uid"] == "local-user" and query["ver"] == "7"
    assert (tmp_path / filename).read_bytes() == b"re-encoded-image"
    assert storage_service.verify_capability(
        filename, query["sig"], query["exp"], query["org"], query["uid"], query["ver"],
    )

    assert _acceptable_avatar_reference(reference, "local-user")
    assert not _acceptable_avatar_reference("/uploads/private-job-result.png", "local-user")
    assert _avatar_url(SimpleNamespace(
        id="local-user",
        avatar_url="/uploads/private-job-result.png",
        signup_metadata={"token_version": 7},
    )) == ""


def test_external_upload_paths_are_not_reissued_as_local_capabilities():
    external = "https://media.example.test/uploads/private-job-result.png"
    assert storage_service.resolve_stored_url(external, user_id="local-user") == external
