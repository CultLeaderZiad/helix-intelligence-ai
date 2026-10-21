from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.db.base import Base
from app.schemas.app_update import AppUpdateResponse
from app.schemas.media import MediaGenerationJobResponse
from app.services import creative_service
from app.services.scraping import adyntel_provider, metapi_provider


class _BrandRows:
    def all(self):
        return [("acme", "Acme", 1)]


class _BrandSession:
    async def scalar(self, query):
        return 1

    async def execute(self, query):
        return _BrandRows()


def test_declarative_base_and_response_models_use_supported_configuration():
    assert Base.metadata is not None

    timestamp = datetime(2026, 10, 21, tzinfo=timezone.utc)
    update = AppUpdateResponse.model_validate(
        SimpleNamespace(
            id="update-1",
            title="Maintenance",
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    assert update.id == "update-1"

    media_job = MediaGenerationJobResponse.model_validate(
        SimpleNamespace(
            id="job-1",
            job_id=None,
            status="completed",
            prompt="A product photo",
            provider="gemini",
            provider_job_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            parameters={},
            result_url=None,
            error_message=None,
            failure_kind=None,
        )
    )
    assert media_job.job_id == "job-1"


@pytest.mark.asyncio
async def test_brand_first_seen_remains_utc_iso8601_z():
    brands = await creative_service.list_brands(_BrandSession())

    first_seen = brands.items[0].first_seen
    assert first_seen.endswith("Z")
    assert datetime.fromisoformat(first_seen.replace("Z", "+00:00")).utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("provider_module", "provider_type", "date_field"),
    [
        (adyntel_provider, adyntel_provider.AdyntelProvider, "start_date_string"),
        (metapi_provider, metapi_provider.MetapiProvider, "creation_time"),
    ],
)
@pytest.mark.parametrize("date_suffix", ["Z", "-05:00"])
def test_provider_dates_are_compared_as_aware_utc(
    monkeypatch, provider_module, provider_type, date_field, date_suffix
):
    now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return now

    monkeypatch.setattr(provider_module, "datetime", FrozenDateTime)
    start = now - timedelta(days=5)
    if date_suffix == "Z":
        start_value = start.isoformat().replace("+00:00", "Z")
    else:
        start_value = start.astimezone(timezone(timedelta(hours=-5))).isoformat()

    provider = provider_type(db=None, org_id="org-test", user_id="user-test")
    creatives = provider._parse_adyntel_ads(
        [{date_field: start_value}], "example.com"
    ) if provider_type is adyntel_provider.AdyntelProvider else provider._parse_metapi_ads(
        [{date_field: start_value}], "example.com"
    )

    assert creatives[0].days_known is True
    assert creatives[0].days_active == 5
    assert creatives[0].first_seen == start_value
