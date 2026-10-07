import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# add backend dir to sys.path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def _clean_async_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    if "sslmode=" in url:
        url = url.replace("sslmode=", "ssl=")
    for bad in ("channel_binding=require&", "&channel_binding=require", "?channel_binding=require"):
        url = url.replace(bad, "" if "&" in bad else "?" if "?" in bad else "")
    return url

custom_url = os.environ.get("TEST_DATABASE_URL")
if custom_url:
    config.set_main_option("sqlalchemy.url", _clean_async_url(custom_url))
elif not config.get_main_option("sqlalchemy.url") or config.get_main_option("sqlalchemy.url") == "driver://user:pass@localhost/dbname":
    config.set_main_option("sqlalchemy.url", settings.async_database_url)

import re

def _norm_json_default(val: str | None) -> str:
    if not val:
        return ""
    v = re.sub(r"::jsonb?", "", str(val)).strip()
    return v.strip("'").strip()


def custom_compare_server_default(
    context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    col_type = str(metadata_column.type).lower()
    if "json" in col_type:
        d1 = _norm_json_default(inspected_default)
        d2 = _norm_json_default(rendered_metadata_default)
        if d1 == d2:
            return False
        return True
    return None


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "index" and name in ("uq_scrape_jobs_active_query", "ix_users_lower_email"):
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    is_sqlite = bool(url and "sqlite" in url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=custom_compare_server_default,
        include_object=include_object,
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    is_sqlite = connection.dialect.name == "sqlite"
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=custom_compare_server_default,
        include_object=include_object,
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
