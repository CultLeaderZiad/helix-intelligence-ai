# Disposable local preview

The repository setup/run commands use installed PostgreSQL 16 binaries, Python project dependencies and pnpm. No cloud database, injected production database URL, provider account or worker is used.

- Setup: `bash .hoplite/scripts/setup-local.sh` (also called by managed workspace setup).
- Run: managed Preview executes `bash .hoplite/scripts/run-local.sh`, supervising API port 8000 and Vite port 3000.
- Database: loopback port 55434, `helix_w6_preview`; data and generated credentials are ignored under `.hoplite/local/`.
- API login: `helix_w6_api`, `NOSUPERUSER NOBYPASSRLS`, inherits `helix_app`. Migrations/seeding use the separate local owner.
- Synthetic identities: `w6-admin@example.com`, `w6-member@example.com`, `w6-pending@example.com`, `w6-other@example.com`. Their generated local-only password is in the ignored, mode-0600 `preview-credentials.json`; never publish that file or browser authentication state.
- Seed is idempotent, creates no creatives/AI/provider results, and does not overwrite users' later mutation checks.

Part A is stopped without an authorized non-production provider key. This fixture-only launcher deliberately unsets provider/email/storage credentials, so it cannot serve as live-provider evidence. A later authorized provider-proof environment must explicitly configure its non-production key outside this launcher.
