"""A platform admin's own workspace is not capped per day (no database needed)."""
from app.schemas.pricing import PlanLimits
from app.services import provider_budget as pb


def test_admin_owner_gets_generous_limits_everyone_else_keeps_theirs():
    assert pb.resolve_limits({"searches_per_day": 3}, False) == {"searches_per_day": 3}
    assert pb.resolve_limits(None, False) == {}
    admin = pb.resolve_limits({"searches_per_day": 3}, True)
    assert admin["_admin"] is True and admin["searches_per_day"] == 1000 and admin["agent_messages_per_day"] == 10000


def test_admin_limits_stay_inside_the_plan_schema_bounds():
    PlanLimits(**{k: v for k, v in pb.ADMIN_LIMITS.items() if k != "_admin"})


def test_admin_provider_call_cap_scales_with_the_admin_search_allowance():
    assert pb.workspace_call_cap(pb.ADMIN_LIMITS) >= 2000
    assert pb.search_cap(pb.ADMIN_LIMITS) == 1000
