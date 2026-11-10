"""Refuse a production process whose database role bypasses row-level security."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.config import classified_environment

logger = logging.getLogger(__name__)

_MESSAGE = (
    "Database role {role} is superuser or BYPASSRLS, so row-level security does not apply. "
    "Point DATABASE_URL at helix_api_login for the API or helix_worker_login for the worker. "
    "See DEVELOPMENT.md. Do not put the password in the repository."
)


async def assert_rls_role(connection) -> None:
    row = (
        await connection.execute(
            text(
                """
                SELECT rolname, rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = current_user
                """
            )
        )
    ).mappings().first()
    if row is None:
        return
    if not (row["rolsuper"] or row["rolbypassrls"]):
        return
    message = _MESSAGE.format(role=row["rolname"])
    if classified_environment() == "production":
        raise RuntimeError(message)
    logger.warning(message)
