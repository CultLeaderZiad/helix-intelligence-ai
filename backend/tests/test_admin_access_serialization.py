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
async def test_batched_access_lookup_skips_absent_workspaces():
    from app.services import billing_service

    class NoQueries:
        async def execute(self, *_a, **_k):
            raise AssertionError("no workspace ids must not query")

    assert await billing_service.access_states_for_orgs(NoQueries(), [None, ""]) == {}


def test_access_state_is_the_same_logic_for_one_and_many():
    import datetime as dt
    from types import SimpleNamespace

    from app.services.billing_service import _access_state

    now = dt.datetime(2026, 11, 8, tzinfo=dt.timezone.utc)
    grant = SimpleNamespace(
        revoked_at=None, expires_at=now + dt.timedelta(days=7), granted_at=now,
        granted_by_user_id="u", feature_flags={"discover": True}, plan_id="p",
    )
    assert _access_state(grant, None, now)["status"] == "approved"
    grant.expires_at = now - dt.timedelta(seconds=1)
    assert _access_state(grant, None, now)["status"] == "expired"
    assert _access_state(None, None, now)["status"] == "pending"
