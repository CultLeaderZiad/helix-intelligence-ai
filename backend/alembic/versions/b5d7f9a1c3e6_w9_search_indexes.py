"""W9-1: full-text search indexes for archive and board search.

GIN indexes over ad_archive and creatives (brand, headline, body, CTA,
landing domain) with the ``simple`` and ``arabic`` configs. They back
``GET /api/archive/search``. The expressions are frozen copies of
app/services/text_search.py.

Additive only: two indexes, no columns. Monthly record counting stays in
``workspace_daily_usage.records`` (migration f2b4d6e8a0c3).

Revision ID: b5d7f9a1c3e6
Revises: a4c6e8f0b2d5
"""

from alembic import op

revision = "b5d7f9a1c3e6"
down_revision = "a4c6e8f0b2d5"
branch_labels = None
depends_on = None

ARCHIVE_DOC = "(to_tsvector('simple'::regconfig, coalesce(ad_archive.brand_name, '') || ' ' || coalesce(ad_archive.headline, '') || ' ' || coalesce(ad_archive.body, '') || ' ' || coalesce(ad_archive.cta, '') || ' ' || coalesce(ad_archive.landing_domain, '')) || to_tsvector('arabic'::regconfig, coalesce(ad_archive.brand_name, '') || ' ' || coalesce(ad_archive.headline, '') || ' ' || coalesce(ad_archive.body, '') || ' ' || coalesce(ad_archive.cta, '') || ' ' || coalesce(ad_archive.landing_domain, '')))"
CREATIVES_DOC = "(to_tsvector('simple'::regconfig, coalesce(creatives.brand_name, '') || ' ' || coalesce(creatives.headline, '') || ' ' || coalesce(creatives.body, '') || ' ' || coalesce(creatives.cta, '') || ' ' || coalesce(creatives.landing_domain, '')) || to_tsvector('arabic'::regconfig, coalesce(creatives.brand_name, '') || ' ' || coalesce(creatives.headline, '') || ' ' || coalesce(creatives.body, '') || ' ' || coalesce(creatives.cta, '') || ' ' || coalesce(creatives.landing_domain, '')))"


def upgrade() -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_ad_archive_fts ON ad_archive USING gin ({ARCHIVE_DOC})")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_creatives_fts ON creatives USING gin ({CREATIVES_DOC})")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_creatives_fts")
    op.execute("DROP INDEX IF EXISTS ix_ad_archive_fts")
