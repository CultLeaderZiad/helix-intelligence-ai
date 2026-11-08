"""Every legal and illegal transition of every Helix state machine."""

import itertools
from types import SimpleNamespace

import pytest

from app.core.state_machines import (
    ACCESS, BOARD_SHARE, CREDIT_RESERVATION, IllegalTransition, MACHINES,
    MONITOR, MONITOR_RUN, SCRAPE_JOB, SUPPORT_TICKET, SUPPORT_TICKET_STATUSES,
    WORK_ITEM, catalog, catalog_markdown,
)

EXPECTED_LEGAL = {
    "scrape_job": {
        ("queued", "running"), ("queued", "failed"), ("queued", "cancelled"), ("queued", "timed_out"),
        ("running", "queued"), ("running", "succeeded"), ("running", "failed"),
        ("running", "cancelled"), ("running", "timed_out"),
    },
    "work_item": {
        ("queued", "leased"), ("queued", "canceled"),
        ("leased", "running"), ("leased", "canceled"), ("leased", "queued"), ("leased", "dead"),
        ("running", "succeeded"), ("running", "queued"), ("running", "dead"), ("running", "canceled"),
    },
    "monitor": {("active", "paused"), ("paused", "active")},
    "monitor_run": {("running", "succeeded"), ("running", "failed")},
    "credit_reservation": {("pending", "settled"), ("pending", "refunded"), ("settled", "refunded")},
    "support_ticket": {(a, b) for a in SUPPORT_TICKET_STATUSES for b in SUPPORT_TICKET_STATUSES if a != b},
    "access": {
        ("pending", "approved"), ("pending", "rejected"), ("rejected", "pending"), ("rejected", "approved"),
        ("approved", "expired"), ("approved", "revoked"), ("expired", "pending"), ("expired", "approved"),
        ("revoked", "pending"), ("revoked", "approved"),
    },
    "board_share": {("active", "expired"), ("active", "revoked")},
}

CASES = [
    (name, a, b)
    for name, m in MACHINES.items()
    for a, b in itertools.product(sorted(m.states), repeat=2)
    if a != b
]


@pytest.mark.parametrize("name,current,target", CASES)
def test_every_pair(name, current, target):
    m = MACHINES[name]
    legal = (current, target) in EXPECTED_LEGAL[name]
    assert m.can(current, target) is legal
    if legal:
        assert m.check(current, target) == target
    else:
        with pytest.raises(IllegalTransition):
            m.check(current, target)


def test_tables_cover_expected_machines():
    assert set(MACHINES) == set(EXPECTED_LEGAL)


@pytest.mark.parametrize("m", list(MACHINES.values()), ids=lambda m: m.name)
def test_terminal_states_have_no_exits_and_self_is_idempotent(m):
    for t in m.terminal:
        assert not m.transitions.get(t)
    for s in m.states:
        assert m.can(s, s)
    assert not m.can("not_a_status", "not_a_status")


@pytest.mark.parametrize("m", list(MACHINES.values()), ids=lambda m: m.name)
def test_initial_states(m):
    for s in m.states:
        assert m.can(None, s) is (s in m.initial)


def test_stored_values_unchanged():
    # Database and API values must not be renamed.
    assert SCRAPE_JOB.terminal == {"succeeded", "failed", "cancelled", "timed_out"}
    assert WORK_ITEM.states == {"queued", "leased", "running", "succeeded", "dead", "canceled"}
    assert MONITOR.states == {"active", "paused"}
    assert MONITOR_RUN.states == {"running", "succeeded", "failed", "skipped"}
    assert CREDIT_RESERVATION.states == {"pending", "settled", "refunded"}
    assert SUPPORT_TICKET.states == {"open", "in_progress", "resolved"}
    assert ACCESS.states == {"pending", "approved", "rejected", "expired", "revoked"}
    assert BOARD_SHARE.states == {"active", "expired", "revoked"}


def test_catalog_is_documented_for_agents():
    data = catalog()
    for m in data["machines"]:
        for s in m["states"]:
            assert s["description"], (m["name"], s["value"])
    md = catalog_markdown()
    assert "## scrape_job" in md and "`timed_out`" in md


def test_discovery_terminal_refuses_finished_job():
    from app.services.discover_service import DISCOVER_TERMINAL_STATUSES, _set_discovery_terminal

    assert DISCOVER_TERMINAL_STATUSES == set(SCRAPE_JOB.terminal)
    job = SimpleNamespace(status="running", stages_total=5)
    _set_discovery_terminal(job, status="succeeded")
    assert job.status == "succeeded" and job.progress == 1.0
    with pytest.raises(IllegalTransition):
        _set_discovery_terminal(job, status="failed")


def test_access_state_values_are_in_table():
    import datetime
    from app.services.billing_service import _access_state

    now = datetime.datetime.now(datetime.timezone.utc)
    grant = SimpleNamespace(revoked_at=None, expires_at=None, granted_at=now,
                            granted_by_user_id=None, feature_flags={}, plan_id=None)
    assert _access_state(grant, None, now)["status"] in ACCESS.states
    assert _access_state(None, None, now)["status"] in ACCESS.states
