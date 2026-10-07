from typing import AsyncGenerator
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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

