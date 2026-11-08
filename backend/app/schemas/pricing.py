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


class PublicPlan(BaseModel):
    id: str
    name: str
    price_monthly: Optional[float] = None
    pricing: PlanPricing


class PublicPricing(BaseModel):
    trial_days: int
    trial_features: List[str]
    plans: List[PublicPlan]
