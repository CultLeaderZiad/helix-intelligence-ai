"""Row-level security on users and api_keys.

``users`` (password and reset-token hashes) and ``api_keys`` had no RLS, so
the restricted API and worker roles could read every row whenever the app's
own filter was missing. This adds the same fail-closed pattern as the tenant
tables. No data is changed.

users — a row is visible to:
* a platform admin scope;
* that user (``helix.user_id``);
* a pre-authentication lookup of exactly that email (``helix.auth_email``,
  set only for sign-in, sign-up and forgot-password);
* the owner and members of a workspace in ``helix.org_ids``.
Writes are limited to a platform admin, the user, or that one email lookup.

api_keys — the standard workspace policy on ``org_id``.

Revision ID: b2d4f6a8c0e3
Revises: f1a3c5e7b9d2
"""

from alembic import op

revision = "b2d4f6a8c0e3"
down_revision = "f1a3c5e7b9d2"
branch_labels = None
depends_on = None

_ORGS = "string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ',')"
_ADMIN = "current_setting('helix.platform_admin', true) = '1'"
_SELF = "users.id = current_setting('helix.user_id', true)"
_EMAIL = (
    "(coalesce(current_setting('helix.auth_email', true), '') <> '' "
    "AND lower(users.email) = current_setting('helix.auth_email', true))"
)
_USERS_READ = (
    f"({_ADMIN} OR {_SELF} OR {_EMAIL} "
    f"OR users.id IN (SELECT o.owner_id FROM organizations o WHERE o.id = ANY ({_ORGS})) "
    f"OR users.id IN (SELECT m.user_id FROM organization_members m WHERE m.org_id = ANY ({_ORGS})))"
)
_USERS_WRITE = f"({_ADMIN} OR {_SELF} OR {_EMAIL})"
_API_KEYS = f"({_ADMIN} OR (api_keys.org_id = ANY ({_ORGS})))"


def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY users_tenant_isolation ON users FOR ALL "
        f"USING {_USERS_READ} WITH CHECK {_USERS_WRITE}"
    )
    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE api_keys NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY api_keys_tenant_isolation ON api_keys FOR ALL "
        f"USING {_API_KEYS} WITH CHECK {_API_KEYS}"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS api_keys_tenant_isolation ON api_keys")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS users_tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
