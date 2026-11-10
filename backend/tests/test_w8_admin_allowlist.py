"""W8: migration f8b3c4d5e6a7 promotes only allowlisted admins (no DB needed)."""
import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "f8b3c4d5e6a7_manual_access_grants.py"
_spec = importlib.util.spec_from_file_location("f8b3_migration", _PATH)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


def test_unset_allowlist_promotes_nobody():
    assert migration.platform_admin_allowlist("") == []


def test_allowlist_is_trimmed_lowercased_and_deduplicated():
    raw = " Owner@Example.org, owner@example.org ,not-an-email, second@helix.io "
    assert migration.platform_admin_allowlist(raw) == ["owner@example.org", "second@helix.io"]


def test_reads_the_environment_by_default(monkeypatch):
    monkeypatch.setenv("HELIX_PLATFORM_ADMIN_EMAILS", "a@b.co")
    assert migration.platform_admin_allowlist() == ["a@b.co"]
    monkeypatch.delenv("HELIX_PLATFORM_ADMIN_EMAILS")
    assert migration.platform_admin_allowlist() == []


def test_the_blanket_promotion_is_gone():
    src = _PATH.read_text(encoding="utf-8")
    assert "WHERE role = 'admin'\")" not in src
    assert "lower(email) = ANY(:emails)" in src
