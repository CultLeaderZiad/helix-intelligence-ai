from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        # Neon pooler (PgBouncer) doesn't support prepared statements
        "statement_cache_size": 0,
        # Allow 30s for Neon free-tier cold-start wake-up
        "command_timeout": 30,
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
        "command_timeout": 30,
    },
)

worker_session_maker = async_sessionmaker(
    worker_engine, expire_on_commit=False
)


def _install_tenant_listener(session_maker) -> None:
    """Re-apply transaction-local tenant settings whenever a transaction begins.

    Context is stored on the task, not the connection. ``set_config(..., true)``
    ends with the transaction, so a pooled connection cannot leak the previous
    organization into the next checkout.
    """

    @event.listens_for(session_maker.class_.sync_session_class, "after_begin")
    def _apply(session, transaction, connection):
        del session, transaction
        if connection.dialect.name != "postgresql":
            return
        from app.core.tenancy import current_tenant

        ctx = current_tenant()
        if ctx is None:
            return
        org_ids = "" if ctx.platform_admin or ctx.org_ids is None else ",".join(ctx.org_ids)
        connection.execute(text("SELECT set_config('helix.user_id', :user_id, true)"), {"user_id": ctx.user_id or ""})
        connection.execute(text("SELECT set_config('helix.org_ids', :org_ids, true)"), {"org_ids": org_ids})
        connection.execute(
            text("SELECT set_config('helix.platform_admin', :flag, true)"),
            {"flag": "1" if ctx.platform_admin else "0"},
        )
        connection.execute(
            text("SELECT set_config('helix.enforce', :flag, true)"),
            {"flag": "1" if ctx.enforce else "0"},
        )


_install_tenant_listener(async_session_maker)
_install_tenant_listener(worker_session_maker)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

