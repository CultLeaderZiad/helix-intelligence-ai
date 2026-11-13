"""Public pricing card for a plan. Full admins edit it; anyone can read listed plans."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_FEATURES = 12
MAX_TEXT = 160


def _clean(items: List[str]) -> List[str]:
    out = []
    for item in items or []:
        text = " ".join(str(item).split())[:MAX_TEXT]
        if text:
            out.append(text)
    return out[:MAX_FEATURES]


class Localized(BaseModel):
    en: str = Field("", max_length=MAX_TEXT)
    ar: str = Field("", max_length=MAX_TEXT)


class LocalizedList(BaseModel):
    en: List[str] = []
    ar: List[str] = []

    @field_validator("en", "ar")
    @classmethod
    def _items(cls, value: List[str]) -> List[str]:
        return _clean(value)


class PlanPricing(BaseModel):
    """Shown on /pricing only when ``listed`` is true."""

    listed: bool = False
    order: int = Field(0, ge=0, le=99)
    tagline: Localized = Localized()
    features: LocalizedList = LocalizedList()
    badge: Localized = Localized()
    highlight: bool = False
    # "trial": start the free trial; "contact": talk to us (no checkout exists).
    cta: Literal["trial", "contact"] = "trial"
    # Shown after the price, e.g. "/ month". Empty means the default period.
    period: Localized = Localized()


class PlanLimits(BaseModel):
    """Server-enforced limits for workspaces on this plan. None = global default.

    searches_per_day: new Discover searches per workspace per UTC day (cache
    hits are free). The workspace's provider-call cap becomes twice this, as
    a brand search can use two provider tasks.
    monitors: active monitors per workspace.
    monitor_cadences: cadences the plan may use ("daily", "weekly").
    records_per_month: Metapi records per workspace per UTC month (Discover
    and monitors together).
    """

    searches_per_day: Optional[int] = Field(None, ge=0, le=1000)
    monitors: Optional[int] = Field(None, ge=0, le=500)
    monitor_cadences: Optional[List[Literal["daily", "weekly"]]] = None
    records_per_month: Optional[int] = Field(None, ge=0, le=100000)

    @field_validator("monitor_cadences")
    @classmethod
    def _cadences(cls, value):
        if value is None:
            return None
        out = sorted(set(value))
        return out or None


class PublicPlan(BaseModel):
    id: str
    name: str
    price_monthly: Optional[float] = None
    pricing: PlanPricing


class PublicPricing(BaseModel):
    trial_days: int
    trial_features: List[str]
    plans: List[PublicPlan]
