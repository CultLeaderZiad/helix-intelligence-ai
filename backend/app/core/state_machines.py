"""One source of truth for every status column Helix writes.

Each ``StateMachine`` names its states, the terminal ones, and the legal
moves between them. Services call ``machine.check(current, target)`` before
writing a status, so an illegal move raises ``IllegalTransition`` instead of
silently corrupting a row. The values are the exact strings already stored
in the database and returned by the API; nothing here renames anything.

``catalog()`` renders all machines as plain data for the API, Markdown and
MCP surfaces, so agents can read what each status means and where it goes.
See docs/w8/state-machines.md for the narrative inventory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping, Optional


class IllegalTransition(ValueError):
    """A status write that the machine's transition table does not allow."""

    def __init__(self, machine: str, current: Optional[str], target: str):
        self.machine = machine
        self.current = current
        self.target = target
        super().__init__(f"{machine}: illegal transition {current!r} -> {target!r}")


@dataclass(frozen=True)
class StateMachine:
    name: str
    initial: FrozenSet[str]
    transitions: Mapping[str, FrozenSet[str]]
    terminal: FrozenSet[str]
    descriptions: Mapping[str, str] = field(default_factory=dict)
    # Statuses that are computed when read, never stored (e.g. access state).
    derived: bool = False

    @property
    def states(self) -> FrozenSet[str]:
        out = set(self.transitions)
        for targets in self.transitions.values():
            out |= set(targets)
        return frozenset(out)

    def is_terminal(self, state: Optional[str]) -> bool:
        return state in self.terminal

    def can(self, current: Optional[str], target: str) -> bool:
        if current is None:
            return target in self.initial
        if current == target:
            # Re-writing the same status is idempotent, except leaving a
            # terminal state open to a second "finish" is still harmless.
            return current in self.states
        return target in self.transitions.get(current, frozenset())

    def check(self, current: Optional[str], target: str) -> str:
        if not self.can(current, target):
            raise IllegalTransition(self.name, current, target)
        return target

    def describe(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "derived": self.derived,
            "initial": sorted(self.initial),
            "terminal": sorted(self.terminal),
            "states": [
                {
                    "value": s,
                    "terminal": s in self.terminal,
                    "next": sorted(self.transitions.get(s, frozenset())),
                    "description": self.descriptions.get(s, ""),
                }
                for s in sorted(self.states)
            ],
        }


def _t(table: Mapping[str, Iterable[str]]) -> Dict[str, FrozenSet[str]]:
    return {k: frozenset(v) for k, v in table.items()}


# --- Discover jobs (scrape_jobs.status) -----------------------------------
SCRAPE_JOB = StateMachine(
    name="scrape_job",
    initial=frozenset({"queued", "running"}),  # running when executed inline
    transitions=_t({
        # queued -> succeeded: a retried job is queued again when the
        # replacement worker finishes it (crash reclaim), as before W8.
        "queued": {"running", "succeeded", "failed", "cancelled", "timed_out"},
        # running -> queued: a retryable provider error schedules a retry.
        "running": {"queued", "succeeded", "failed", "cancelled", "timed_out"},
        "succeeded": set(),
        "failed": set(),
        "cancelled": set(),
        "timed_out": set(),
    }),
    terminal=frozenset({"succeeded", "failed", "cancelled", "timed_out"}),
    descriptions={
        "queued": "Accepted and waiting for a worker (also after a retry is scheduled).",
        "running": "A worker holds the job; see `stage` for the step (init, scoring, ...).",
        "succeeded": "Finished; results are readable. Zero results is still succeeded.",
        "failed": "Stopped with an error; reserved credits were refunded.",
        "cancelled": "Stopped by the user; reserved credits were refunded.",
        "timed_out": "Passed its server deadline; reserved credits were refunded.",
    },
)
SCRAPE_JOB_ACTIVE = frozenset({"queued", "running"})

# --- Outbox work items (work_items.status) --------------------------------
# Note the US spelling "canceled" here versus "cancelled" on scrape_jobs.
WORK_ITEM = StateMachine(
    name="work_item",
    initial=frozenset({"queued"}),
    transitions=_t({
        "queued": {"leased", "canceled"},
        "leased": {"running", "canceled", "queued", "dead"},
        "running": {"succeeded", "queued", "dead", "canceled"},
        "succeeded": set(),
        "dead": set(),
        "canceled": set(),
    }),
    terminal=frozenset({"succeeded", "dead", "canceled"}),
    descriptions={
        "queued": "Waiting until available_at; claimable by a worker.",
        "leased": "Claimed by a worker under a short lease, not yet started.",
        "running": "Executing; the lease is extended by heartbeats.",
        "succeeded": "Done.",
        "dead": "Gave up after max_attempts (dead letter).",
        "canceled": "Cancelled before or during execution.",
    },
)

# --- Monitors and their runs ----------------------------------------------
MONITOR = StateMachine(
    name="monitor",
    initial=frozenset({"active"}),
    transitions=_t({"active": {"paused"}, "paused": {"active"}}),
    terminal=frozenset(),
    descriptions={
        "active": "Runs on its cadence when next_run_at is due.",
        "paused": "Not scheduled. paused_reason says why (user, failures, quota, owner gone).",
    },
)

MONITOR_RUN = StateMachine(
    name="monitor_run",
    initial=frozenset({"running", "skipped"}),
    transitions=_t({
        "running": {"succeeded", "failed"},
        "succeeded": set(),
        "failed": set(),
        "skipped": set(),
    }),
    terminal=frozenset({"succeeded", "failed", "skipped"}),
    descriptions={
        "running": "Search in flight for this monitor.",
        "succeeded": "Run finished and changes were recorded.",
        "failed": "Run failed; counts toward consecutive_failures.",
        "skipped": "Not run (for example a run was already in flight).",
    },
)

# --- Credit reservations ----------------------------------------------------
CREDIT_RESERVATION = StateMachine(
    name="credit_reservation",
    initial=frozenset({"pending", "settled"}),  # settled directly for sync charges
    transitions=_t({
        "pending": {"settled", "refunded"},
        # settled -> refunded: a finished job can still be refunded on failure.
        "settled": {"refunded"},
        "refunded": set(),
    }),
    terminal=frozenset({"refunded"}),
    descriptions={
        "pending": "Credits held for in-flight work.",
        "settled": "Charge recorded in the usage log.",
        "refunded": "Credits returned; cannot be settled again.",
    },
)

# --- Support tickets --------------------------------------------------------
SUPPORT_TICKET = StateMachine(
    name="support_ticket",
    initial=frozenset({"open"}),
    # Staff may set any status; replies move open->in_progress (staff) and
    # resolved->open (customer).
    transitions=_t({
        "open": {"in_progress", "resolved"},
        "in_progress": {"open", "resolved"},
        "resolved": {"open", "in_progress"},
    }),
    terminal=frozenset(),
    descriptions={
        "open": "Waiting for staff.",
        "in_progress": "Staff replied or picked it up.",
        "resolved": "Closed; a customer reply reopens it.",
    },
)
SUPPORT_TICKET_STATUSES = ("open", "in_progress", "resolved")

# --- Derived (read-time) states --------------------------------------------
ACCESS = StateMachine(
    name="access",
    derived=True,
    initial=frozenset({"pending"}),
    transitions=_t({
        "pending": {"approved", "rejected"},
        "rejected": {"pending", "approved"},
        "approved": {"expired", "revoked"},
        "expired": {"pending", "approved"},
        "revoked": {"pending", "approved"},
    }),
    terminal=frozenset(),
    descriptions={
        "pending": "No active grant; a request is waiting (or none was made yet).",
        "approved": "An unrevoked grant whose expiry is in the future (or none).",
        "rejected": "The latest request was rejected.",
        "expired": "The grant's expires_at has passed.",
        "revoked": "An admin revoked the grant; data is retained.",
    },
)

BOARD_SHARE = StateMachine(
    name="board_share",
    derived=True,
    initial=frozenset({"active"}),
    transitions=_t({"active": {"expired", "revoked"}, "expired": set(), "revoked": set()}),
    terminal=frozenset({"expired", "revoked"}),
    descriptions={
        "active": "Link resolves until expires_at.",
        "expired": "expires_at has passed.",
        "revoked": "revoked_at is set.",
    },
)

MACHINES: Dict[str, StateMachine] = {
    m.name: m
    for m in (
        SCRAPE_JOB, WORK_ITEM, MONITOR, MONITOR_RUN,
        CREDIT_RESERVATION, SUPPORT_TICKET, ACCESS, BOARD_SHARE,
    )
}


def catalog() -> Dict[str, object]:
    return {"machines": [m.describe() for m in MACHINES.values()]}


def catalog_markdown() -> str:
    lines = ["# Helix status values", ""]
    for m in MACHINES.values():
        kind = " (derived at read time)" if m.derived else ""
        lines += [f"## {m.name}{kind}", "", "| status | terminal | next | meaning |", "|---|---|---|---|"]
        for s in m.describe()["states"]:  # type: ignore[index]
            nxt = ", ".join(s["next"]) or "-"
            lines.append(f"| `{s['value']}` | {'yes' if s['terminal'] else 'no'} | {nxt} | {s['description']} |")
        lines.append("")
    return "\n".join(lines)
