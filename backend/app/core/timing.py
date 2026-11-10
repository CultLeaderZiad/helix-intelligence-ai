"""Opt-in per-request timing, emitted as a ``Server-Timing`` header.

Enabled only when ``SERVER_TIMING_ENABLED`` is true. Spans:

* ``connect`` — opening a new DB connection (TCP + TLS + Postgres auth)
* ``ping``    — ``pool_pre_ping`` liveness checks on checkout
* ``db``      — every SQL statement, including RLS ``set_config`` calls
* ``rls``     — the tenant ``set_config`` statements alone (subset of ``db``)
* ``hash``    — password hash verification
* ``app``     — total minus the above (Python, serialization, everything else)

Each span reports its duration and how many times it ran, so round-trip
counts are visible separately from this machine's network latency.
"""
from __future__ import annotations

import contextvars
import time
from contextlib import asynccontextmanager, contextmanager

_current: contextvars.ContextVar["RequestTiming | None"] = contextvars.ContextVar(
    "helix_request_timing", default=None
)
_connect_started: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "helix_connect_started", default=None
)
_installed = False
_instrumented_engines: set[int] = set()


class RequestTiming:
    __slots__ = ("durations", "counts", "started")

    def __init__(self) -> None:
        self.durations: dict[str, float] = {}
        self.counts: dict[str, int] = {}
        self.started = time.perf_counter()

    def add(self, name: str, seconds: float) -> None:
        self.durations[name] = self.durations.get(name, 0.0) + seconds
        self.counts[name] = self.counts.get(name, 0) + 1

    def header(self) -> str:
        total = time.perf_counter() - self.started
        accounted = sum(v for k, v in self.durations.items() if k != "rls")
        parts = [
            f'{name};dur={self.durations[name] * 1000:.1f};desc="n={self.counts[name]}"'
            for name in ("connect", "ping", "db", "rls", "hash")
            if name in self.durations
        ]
        parts.append(f"app;dur={max(total - accounted, 0) * 1000:.1f}")
        parts.append(f"total;dur={total * 1000:.1f}")
        return ", ".join(parts)


def current() -> RequestTiming | None:
    return _current.get()


def start_request() -> tuple[RequestTiming, contextvars.Token]:
    timing = RequestTiming()
    return timing, _current.set(timing)


def end_request(token: contextvars.Token) -> None:
    _current.reset(token)


def record(name: str, seconds: float) -> None:
    timing = _current.get()
    if timing is not None:
        timing.add(name, seconds)


@contextmanager
def span(name: str):
    if _current.get() is None:
        yield
        return
    started = time.perf_counter()
    try:
        yield
    finally:
        record(name, time.perf_counter() - started)


@asynccontextmanager
async def aspan(name: str):
    with span(name):
        yield


def install_engine_timing(async_engine) -> None:
    """Attach statement/connect/ping timing to an engine (idempotent per engine)."""
    from sqlalchemy import event

    sync_engine = async_engine.sync_engine
    if id(sync_engine) in _instrumented_engines:
        return
    _instrumented_engines.add(id(sync_engine))

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("helix_timing_stack", []).append(time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.get("helix_timing_stack")
        if stack:
            record("db", time.perf_counter() - stack.pop())

    @event.listens_for(sync_engine, "do_connect")
    def _do_connect(dialect, conn_rec, cargs, cparams):
        _connect_started.set(time.perf_counter())

    @event.listens_for(sync_engine.pool, "connect")
    def _connected(dbapi_connection, connection_record):
        started = _connect_started.get()
        if started is not None:
            record("connect", time.perf_counter() - started)
            _connect_started.set(None)

    dialect = sync_engine.dialect
    original_ping = dialect.do_ping

    def timed_ping(dbapi_connection):
        with span("ping"):
            return original_ping(dbapi_connection)

    dialect.do_ping = timed_ping


def install(app, engines) -> None:
    """Register the middleware and engine hooks once."""
    global _installed
    if _installed:
        return
    _installed = True
    for engine in engines:
        install_engine_timing(engine)

    @app.middleware("http")
    async def server_timing(request, call_next):
        timing, token = start_request()
        try:
            response = await call_next(request)
        finally:
            end_request(token)
        response.headers["Server-Timing"] = timing.header()
        return response
