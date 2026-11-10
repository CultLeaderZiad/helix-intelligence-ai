# W8 release checklist (draft, not approved)

Nothing here has been run on production. Production, Render and Vercel are
untouched; merging `fix/core-W8` needs Ziad's explicit OK.

## 1. Migrations

**Production database = Neon branch `dev`** (`br-gentle-star-axcrbk22`, endpoint
`ep-cold-rice-axydlqmv`), proven server-side (`neon.branch_id`) with the URL in
Render's environment export on 2026-11-10. It is at **`b1c2d3e4f5a6`** (row 4 below),
230 users. The branch named `production` (`br-soft-mode-ax44ab32`) is an empty
leftover and is NOT used. **Re-read the revision (read-only) right before release.**

From `b1c2d3e4f5a6` to head `c9e1f3a5b7d0` there are **22 migrations** (rows 5–26),
run from a local machine as the owner on the **direct** host
(`alembic upgrade head`), never via Render. Rows 1–4 are already applied on `dev`.
The cutover runbook is `docs/w8/release-plan.md`.

| # | Revision | What it does | Changes existing data? |
|---|---|---|---|
| 1 | `3c8be5787f7a` | Add MediaGenerationJob | no |
| 2 | `51fc8263b0bc` | Add WebhookEvent | no |
| 3 | `a1b2c3d4e5f6` | Add leadgen tables | no |
| 4 | `b1c2d3e4f5a6` | Production schema alignment | yes (alignment) |
| 5 | `d5e8c0a1b2f3` | Unique Neon auth webhook ids | no |
| 6 | `e7c1a9b4d2f0` | Tenancy, decimal ledger, RLS; creates `helix_app` / `helix_worker` | yes: deletes patterns with no workspace |
| 7 | `f8b3c4d5e6a7` | Manual access grants and flags | yes: admins become platform admins |
| 8 | `c2a4e8b1d907` | Durable work items, provenance | no |
| 9 | `d4f6a8c0e2b1` | Null unmeasured lift, role grants | yes: lift 0 becomes null |
| 10 | `e8c3b5d7a2f4` | Drop leftover defaults, usage-log tenancy | yes: backfills/deletes unattributable usage logs |
| 11 | `f3d9a7c2b1e4` | RLS fails closed | policies only |
| 12 | `a9d4e6f8c2b0` | Discovery cache identity | indexes |
| 13 | `b7e4c9a1d2f0` | Revalidate alignment invariants | stops if required timestamps are null |
| 14 | `d1f9c4a7b263` | Discover job deadline | no |
| 15 | `a3e5c7d9f1b2` | Index organizations.owner_id | no |
| 16 | `b7d2f4a6c8e1` | Guest board links | no |
| 17 | `c4e6a8b0d2f3` | Ad archive | no |
| 18 | `a8c1e4b2d6f0` | Drop creatives.days_active default | no |
| 19 | `e2b4d6f8a0c1` | Search drafts | no |
| 20 | `f1a3c5e7b9d2` | Global daily provider-call counter (added 2026-11-07) | no |
| 21 | `b2d4f6a8c0e3` | RLS on `users` and `api_keys` (added 2026-11-07) | policies only |
| 22 | `d3f5a7b9c1e4` | Per-workspace daily search/provider counters (added 2026-11-07) | no |
| 23 | `e5a7c9d1f3b6` | Monthly per-provider record counter (added 2026-11-08) | no |
| 24 | `a6c8e0f2b4d7` | Public pricing card per plan (added 2026-11-08) | no |
| 25 | `b8d0f2a4c6e9` | Per-plan limits: searches/day, monitors, cadences (added 2026-11-08) | no |
| 26 | `c9e1f3a5b7d0` | Reconcile drifted schemas: defaults, timestamptz, NOT NULL, cascade FKs; no-op on a clean DB (added 2026-11-08) | fills 1 NULL with its default on the live copy |

Evidence: all 22 rehearsed in one run on fresh copies of `dev` (`w8-dev-rehearsal-2`,
2026-11-08; `w8-cutover-rehearsal`, 2026-11-10): no errors, row counts unchanged except
2 workspace-less patterns moved to `pattern_quarantine`, `alembic check` clean.

## 2. Before and after the migrations

Follow the free-plan cutover runbook in `docs/w8/release-plan.md` (backup branch,
local migrations, roles by SQL, Render env with auto-deploy off, manual deploy,
rollback that restores the owner `DATABASE_URL`). First admin: the migration promotes
only `HELIX_PLATFORM_ADMIN_EMAILS`; otherwise use
`backend/scripts/bootstrap_platform_admin.py --expect-branch br-gentle-star-axcrbk22`.

## 3. Provider budgets

### What the counters count

One reservation is taken **before each provider task or model call**, in an
atomic upsert, both globally (`provider_call_budget`) and per workspace
(`workspace_daily_usage.provider_calls`). Refused reservations are rolled back;
errors refuse the call. Refunds never lower them.

| Outbound path | Counted? | Notes |
|---|---|---|
| Metapi keyword task (one per attempt) | yes | `count` = `METAPI_RESOLVE_COUNT` records |
| Metapi advertiser task (brand page) | yes, separately | `count` = 15 records |
| Adyntel, Meta Graph, Apify attempts | yes | one each when configured |
| Job retries (`WORK_MAX_ATTEMPTS`, default 3) | yes | each attempt reserves again |
| Monitor runs | yes | same pipeline |
| Query translation (Groq) | yes | only for mixed-language queries |
| Metapi status polls and the results read | **no** | HTTP requests inside one task; worst case about 28 polls per task (`METAPI_POLL_TIMEOUT_S` 150) |
| Entity-intent model call (Groq) | **no** | gap; only runs when `GROQ_API_KEY` is set |
| Pattern scoring AI (Gemini/Groq/OpenRouter, up to `AI_MAX_RETRIES` retries) | **no** | gap; credit-reserved, but credits are released when it fails |
| ScrapeGraph landing-page enrichment (≤ 2 per search) | **no** | gap; only when `SCRAPEGRAPH_API_KEY` is set |

The daily counters are an **aggregate** across providers. Metapi bills
**records**, so each Metapi task also reserves its `count` against
`METAPI_MONTHLY_RECORD_BUDGET` (default 3,000 per UTC calendar month,
`provider_record_budget`) before it is created; past it, the search stops
with `provider_budget` and is refunded. Metapi's own period resets on the 30th,
not the 1st, so set the budget to the remaining records when going live.

### Metapi allowance

- **Verified from the Metapi dashboard on 2026-11-08 (screenshot from Ziad):**
  Free plan, 850 of 3,000 records used, 2,150 remaining, resets 2026-11-30.
  18 requests this period, all succeeded (≈ 47 records per task, matching the
  old uncapped default of 50). 2,150 records over the ~22 days left is about
  97 records/day, so the proposed settings below (≤ 90/day) fit.
- Metapi's API docs (read 2026-11-07) list: Free 3,000 records/month (hard
  block, `402 quota_exceeded`), Lite 25,000, Pro 100,000; Free rate limits
  120 requests/min and 1,000 requests/day.
- The "25" seen in the proof was Helix's own `DISCOVER_DAILY_PROVIDER_CALL_CAP`
  raised for one test day, not a Metapi limit.

### Settings (now the code defaults, sized for Metapi Free)

3,000 records/month is about 96 records/day.

| Setting | Old default | Default now | Why |
|---|---|---|---|
| `METAPI_RESOLVE_COUNT` | 30 | 15 (the minimum) | a brand search becomes ≤ 30 records (15 keyword + 15 advertiser) |
| `DISCOVER_DAILY_PROVIDER_CALL_CAP` | 300 | 6 | 6 tasks × ≤ 15 records = ≤ 90 records/day |
| `DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE` | 60 | 6 (lower when several workspaces are granted) | one workspace cannot exceed the daily records |
| `DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY` | 50 | 3 | a brand search uses up to 2 tasks |
| `WORK_MAX_ATTEMPTS` | 3 | 3 | retries already count against the caps |

Metapi requests at that cap: ≤ 6 tasks × (1 create + ≤ 28 polls + 1 read) ≈
180/day, under 1,000/day. On Lite (≈ 800 records/day) the caps could rise to
about 50 tasks/day.

## 4. Open gaps

1. The Metapi account plan and current usage are unverified (dashboard).
2. The monthly records counter starts at 0; Metapi already shows 850 used, so
   set `METAPI_MONTHLY_RECORD_BUDGET` to the remaining 2,150 for November.
3. Entity-intent, pattern-scoring and ScrapeGraph calls are not under the
   provider budget.
4. Production's revision (`dev`, `b1c2d3e4f5a6`) should be re-read before release.
5. `dev` has 29 `role='admin'` users (most on test domains); the admin API trusts
   `role`, so run the reviewed `docs/w8/admin-cleanup.sql` (with approval) first.
6. R2 is not configured, so archived media would sit on ephemeral disk.

## 5. Rollback

- Vercel and Render: redeploy the previous deployment (`5b45806`); free Render keeps
  only the last 2 deploys for rollback. Also restore the owner `DATABASE_URL`, because
  the old code expects it (see `docs/w8/release-plan.md`).
- Database: down-migrations cannot restore deleted rows. Restore from the
  pre-release Neon branch or point-in-time restore.
