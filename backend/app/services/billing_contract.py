"""Main-Helix billing provider boundary.

The repository has organization plans, credit balances, and a Neon auth
webhook. It does not contain a checkout provider, price catalog, or the
event schema that would map a paid subscription onto those rows. This
module refuses provider events instead of inventing that contract.
"""

from typing import Any, Dict, List

from fastapi import HTTPException

# What a verified contract would have to supply before any event is applied.
# These are names of missing artifacts, not invented prices or statuses.
MISSING_BILLING_CONTRACT: List[str] = [
    "billing provider identity (the repo has no Stripe, Lemon Squeezy, Paddle, or other checkout integration)",
    "provider signing protocol: header names, signature format, and timestamp window",
    "durable provider event id and the event type catalog",
    "map from provider subscription status onto organizations.status",
    "provider price identifiers and the plan_id each price grants",
    "entitlement flag grants per price (plans.feature_flags is the only flag source in this repo)",
    "downgrade, cancellation, failed-payment, and expiry effects that the provider documents",
]


def billing_contract_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "billing_provider_contract_missing",
            "message": (
                "Paid subscription events are refused. This service has no verified "
                "main-Helix billing provider contract, so it will not invent checkout, "
                "prices, or entitlement grants."
            ),
            "missing": list(MISSING_BILLING_CONTRACT),
        },
    )


def refuse_billing_provider_event(payload: Dict[str, Any] | None = None) -> None:
    """Fail closed. The payload is not interpreted and no row is written."""
    del payload
    raise billing_contract_error()
