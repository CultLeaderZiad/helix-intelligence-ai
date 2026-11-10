from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_S,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE_S,
    connect_args={
        # Neon pooler (PgBouncer, transaction mode) doesn't support prepared statements.
        "statement_cache_size": 0,
        "command_timeout": settings.DB_COMMAND_TIMEOUT_S,
    },
)

async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False
)

# Dedicated worker engine using NullPool to prevent event loop cross-contamination (F24)
worker_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "command_timeout": settings.DB_COMMAND_TIMEOUT_S,
    },
)

worker_session_maker = async_sessionmaker(
    worker_engine, expire_on_commit=False
)


_listened_session_classes: set = set()


def _install_tenant_listener(session_maker) -> None:
    """Re-apply transaction-local tenant settings whenever a transaction begins.

    Context is stored on the task, not the connection. ``set_config(..., true)``
    ends with the transaction, so a pooled connection cannot leak the previous
    organization into the next checkout.
    """

    from app.core.tenancy import RLS_APPLIED_KEY

    sync_session_class = session_maker.class_.sync_session_class
    # The API and worker session makers share one Session class; listening
    # twice ran every transaction's RLS statement twice.
    if sync_session_class in _listened_session_classes:
        return
    _listened_session_classes.add(sync_session_class)

    @event.listens_for(sync_session_class, "after_begin")
    def _apply(session, transaction, connection):
        del transaction
        session.info.pop(RLS_APPLIED_KEY, None)
        if connection.dialect.name != "postgresql":
            return
        from app.core.tenancy import TENANT_SETTINGS_SQL, current_tenant, tenant_settings_params
        from app.core.timing import span

        ctx = current_tenant()
        if ctx is None:
            return
        params = tenant_settings_params(ctx)
        with span("rls"):
            connection.execute(TENANT_SETTINGS_SQL, params)
        session.info[RLS_APPLIED_KEY] = params

    @event.listens_for(sync_session_class, "after_transaction_end")
    def _forget(session, transaction):
        # Any end, savepoints included: ROLLBACK TO SAVEPOINT reverts
        # set_config(..., true), so the next apply must run again.
        del transaction
        session.info.pop(RLS_APPLIED_KEY, None)


_install_tenant_listener(async_session_maker)
_install_tenant_listener(worker_session_maker)


def _single_round_trip_ping(dbapi_connection) -> bool:
    """``pool_pre_ping`` in one round trip.

    SQLAlchemy's asyncpg ping wraps ``fetchrow(";")`` in BEGIN/ROLLBACK, about
    four network round trips per checkout (measured ~600 ms at 150 ms RTT).
    A parameterless ``execute`` uses the simple-query protocol: no prepared
    statement and no explicit transaction, so it is equally safe behind Neon's
    PgBouncer pooler. (Not ``";"``: asyncpg fails on an empty query's missing
    command tag.) Errors still go through the adapter so disconnects
    invalidate the connection exactly as before.
    """
    try:
        dbapi_connection.await_(dbapi_connection._connection.execute("SELECT 1"))
    except Exception as error:  # noqa: BLE001 - adapter re-raises as DBAPI error
        dbapi_connection._handle_exception(error)
    return True


for _engine in (engine, worker_engine):
    if _engine.dialect.name == "postgresql" and _engine.dialect.driver == "asyncpg":
        _engine.dialect.do_ping = _single_round_trip_ping


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

