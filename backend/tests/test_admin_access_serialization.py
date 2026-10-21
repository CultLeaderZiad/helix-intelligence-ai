from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.admin import AdminOrganizationRow, AdminUserRow
from app.services import admin_service


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc), "2026-01-02T03:04:05Z"),
        (
            datetime(2026, 1, 2, 6, 4, 5, tzinfo=timezone(timedelta(hours=3))),
            "2026-01-02T03:04:05Z",
        ),
        (datetime(2026, 1, 2, 3, 4, 5), "2026-01-02T03:04:05Z"),
    ],
)
def test_admin_datetime_serialization_is_valid_utc(value, expected):
    assert admin_service._iso_utc(value) == expected
    assert "+00:00Z" not in admin_service._iso_utc(value)


def test_access_status_fields_are_optional_for_unavailable_workspaces():
    assert AdminOrganizationRow.model_fields["access_status"].default is None
    assert AdminUserRow.model_fields["access_status"].default is None


@pytest.mark.asyncio
async def test_access_status_serializer_returns_none_without_workspace(monkeypatch):
    async def unexpected_lookup(_db, _org_id):
        raise AssertionError("an absent workspace must not trigger access lookup")

    monkeypatch.setattr(admin_service, "access_status_for_org", unexpected_lookup)
    assert await admin_service._organization_access_status(object(), None) is None
