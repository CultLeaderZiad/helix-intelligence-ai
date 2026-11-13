"""W9-1: full-text search indexes and a per-workspace monthly record counter.

* GIN indexes over ad_archive and creatives (brand, headline, body, CTA,
  landing domain) with the ``simple`` and ``arabic`` configs. They back
  ``GET /api/archive/search``. The expressions are frozen copies of
  app/services/text_search.py.
* ``workspace_daily_usage.metapi_records``: Metapi records a workspace
  reserved that UTC day. The monthly cap sums the current month. The table
  already has tenant RLS and app grants, so no policy changes.

Additive only: two indexes and one column with a default.

Revision ID: f2b4c6d8e0a1
Revises: e1a3c5e7f9b2
"""

import sqlalchemy as sa
from alembic import op

revision = "f2b4c6d8e0a1"
down_revision = "e1a3c5e7f9b2"
branch_labels = None
depends_on = None

ARCHIVE_DOC = "(to_tsvector('simple'::regconfig, coalesce(ad_archive.brand_name, '') || ' ' || coalesce(ad_archive.headline, '') || ' ' || coalesce(ad_archive.body, '') || ' ' || coalesce(ad_archive.cta, '') || ' ' || coalesce(ad_archive.landing_domain, '')) || to_tsvector('arabic'::regconfig, coalesce(ad_archive.brand_name, '') || ' ' || coalesce(ad_archive.headline, '') || ' ' || coalesce(ad_archive.body, '') || ' ' || coalesce(ad_archive.cta, '') || ' ' || coalesce(ad_archive.landing_domain, '')))"
CREATIVES_DOC = "(to_tsvector('simple'::regconfig, coalesce(creatives.brand_name, '') || ' ' || coalesce(creatives.headline, '') || ' ' || coalesce(creatives.body, '') || ' ' || coalesce(creatives.cta, '') || ' ' || coalesce(creatives.landing_domain, '')) || to_tsvector('arabic'::regconfig, coalesce(creatives.brand_name, '') || ' ' || coalesce(creatives.headline, '') || ' ' || coalesce(creatives.body, '') || ' ' || coalesce(creatives.cta, '') || ' ' || coalesce(creatives.landing_domain, '')))"


def upgrade() -> None:
    op.add_column(
        "workspace_daily_usage",
        sa.Column("metapi_records", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_ad_archive_fts ON ad_archive USING gin ({ARCHIVE_DOC})")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_creatives_fts ON creatives USING gin ({CREATIVES_DOC})")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_creatives_fts")
    op.execute("DROP INDEX IF EXISTS ix_ad_archive_fts")
    op.drop_column("workspace_daily_usage", "metapi_records")
