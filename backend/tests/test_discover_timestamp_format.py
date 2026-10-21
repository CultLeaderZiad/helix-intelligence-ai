import datetime
from types import SimpleNamespace

import pytest

from app.services.discover_service import _isoformat_utc, _job_response


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            datetime.datetime(2026, 10, 21, 12),
            datetime.datetime(2026, 10, 21, 12, tzinfo=datetime.timezone.utc),
        ),
        (
            datetime.datetime(
                2026, 10, 21, 7,
                tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
            ),
            datetime.datetime(2026, 10, 21, 12, tzinfo=datetime.timezone.utc),
        ),
    ],
)
def test_isoformat_utc_handles_naive_and_aware_datetimes(value, expected):
    serialized = _isoformat_utc(value)

    assert serialized.endswith("Z")
    assert datetime.datetime.fromisoformat(serialized.replace("Z", "+00:00")) == expected


def test_job_response_serializes_legacy_naive_and_aware_dates_as_valid_utc():
    job = SimpleNamespace(
        id="job-1",
        status="succeeded",
        progress=1,
        stage="complete",
        stage_label="Complete",
        stage_index=1,
        stages_total=1,
        record_count=1,
        elapsed_ms=10,
        created_at=datetime.datetime(2026, 10, 21, 12),
        completed_at=datetime.datetime(
            2026, 10, 21, 8,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-4)),
        ),
        deadline_at=datetime.datetime(2026, 10, 21, 13, tzinfo=datetime.timezone.utc),
        error_msg=None,
        failure_kind=None,
        entity_profile=None,
    )

    response = _job_response(job)

    assert response.created_at == "2026-10-21T12:00:00Z"
    assert response.completed_at == "2026-10-21T12:00:00Z"
    assert response.deadline_at == "2026-10-21T13:00:00Z"
