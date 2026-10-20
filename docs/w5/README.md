# W5 — Discover reliability and focused product

Draft work on `fix/intelligence-W5`, based on W4 `eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957`.

The reference audit is `audit/helix-full` (`a7d5628`), not a claim about current production behavior. This branch does not deploy, merge, access production data/accounts, or add billing/pricing features. Only local disposable databases/test identities are used; no fabricated provider output is displayed.

## Verification baseline

- `pnpm typecheck`: exit 2, 483 diagnostics.
- `pnpm exec eslint src -f json`: exit 1, 159 errors.
- Full `python -m pyflakes backend/app`: exit 1, 127 diagnostics.
- Baseline screenshots: `screens/before-landing-en.png` captured from the local managed preview before W5 changes.

Implementation and integrated browser verification are in progress. Final A–E changes, exit codes, before/after counts, screenshots, unresolved controls and the single P0 next step will replace this checkpoint. Do not treat this draft as release-ready.
