# Phase 3 release runbook (2026-11-24)

Branch: `claude/app-features-improvements-gjkvnh`. **Nothing here has been applied to production.** The owner runs the production steps. This file is the checklist.

## What ships

| Item | Commit | Needs |
|---|---|---|
| Monitor fixes (bounded restart retry, record budget before claim/charge) | `a70ca6c` | nothing new |
| 3.1 Telegram and webhook alerts | `d42e052` | migration; Telegram is off until `TELEGRAM_BOT_TOKEN` is set |
| 3.2 Advertiser page, winner signals | `bc9194d` | migration (indexes) |
| 3.3 AI teardown | `394c8bb` | migration; an AI key |
| 3.4 Knowledge base (admin) | `c6c8ce7` | migration; the merged `knowledge_base.md` uploaded by the admin |
| 3.5 Ask Helix (agent, drafts, brief) | `e7241c6` | migration; an AI key |
| 3.6 Public API | **postponed** by the owner | n/a |

## Migrations (production is at `c6e8a0b2d4f7`)

Rehearsed locally on Postgres 16 from `c6e8a0b2d4f7`, with `alembic check` clean after:

```
c6e8a0b2d4f7 -> d7f9b1c3e5a8  Alerts: Telegram chats and signed webhooks per workspace
d7f9b1c3e5a8 -> e8a0c2d4f6b9  Advertiser page: indexes
e8a0c2d4f6b9 -> f9b1d3e5a7c0  AI teardown cache (shared, public ad copy only)
f9b1d3e5a7c0 -> a1c3e5f7b9d2  Knowledge base: documents, chunks, audit
a1c3e5f7b9d2 -> b2d4f6a8c0e1  Helix Agent: cached generations per workspace
```

- All five are **additive**: new tables and indexes only. The only `UPDATE`/`DELETE` text in them is inside `GRANT` lines. The old code keeps working on the new schema.
- Tenant tables with RLS and a policy: `notification_channels`, `agent_generations`. `ad_teardowns`, `kb_documents`, `kb_chunks` and `kb_audit` are platform-wide on purpose (no workspace data).
- One head: `b2d4f6a8c0e1`. Every migration has a downgrade.

## Owner steps, in order

1. **Merge** the branch (open a PR first; none is open yet). Wait for CI.
2. **Backup:** a Neon branch of `dev` (`br-gentle-star-axcrbk22`, which is production), e.g. `backup-pre-phase3-<date>`. Record its id. Do not touch other branches.
3. **Migrate from your machine** with the owner URL on the **direct** host (no `-pooler`), in your shell only:
   `python -m alembic upgrade head`, then `python -m alembic check`.
   Expect the five lines above and `b2d4f6a8c0e1 (head)`.
4. **Render env vars** (names only; set the values yourself): `GROQ_API_KEY` (done by the owner). Optional: `OPENROUTER_API_KEY`, `GEMINI_API_KEY` as fallbacks. Telegram, if wanted: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, then call Telegram `setWebhook` once (see DEVELOPMENT.md "Alerts").
5. **Manual deploy** of the merge commit on Render (auto-deploy stays off).
6. **Verify:**
   - `GET /api/health`: `db: connected`, `migration.up_to_date: true`, `database_revision: b2d4f6a8c0e1`.
   - In the app: Settings shows "Alerts", an ad detail shows "Analyse this ad", `/agent` loads and shows usage, Admin has "Knowledge Base".
   - Ask one question in Ask Helix and analyse one ad. These make the first real AI calls and are the first proof that the Groq key works (not verified yet).
7. **Knowledge base:** send the source files, run `python backend/scripts/kb_merge.py <dir> -o knowledge_base.md`, review the file, and upload it in Admin → Knowledge Base.

## Rollback

Redeploy the previous Render commit. The old code works on the new schema. Run `alembic downgrade c6e8a0b2d4f7` **only** with the owner's approval: it drops the five new feature tables and their data. The backup branch is the data restore point.

## Verified / not verified

- **Verified:** backend 750 passed, 1 skipped (needs the `psql` client; CI has it) on a fresh local Postgres 16. Frontend 265 tests, typecheck, lint clean. Migration rehearsal above. Working tree has no key-shaped strings. The two tracked env files hold public URLs only.
- **Not verified:** any real AI provider call, a real Telegram message, a real signed webhook, the UI in a browser, CI for this branch (no PR yet), production migration state.
- **History note:** old commits contain key-shaped strings, all in deleted test files. Examples: `test_key = "AIzaSyD-m…"` in `test_byok_suite.py`, and `sk-this…` / `sk-imag…` fixtures. They look like test values, not real keys, but the repo is public. If any of them was ever real, revoke it.

## Plans and Whop (waiting on the owner)

Whop checkout and webhook are merged and off. Before turning them on: decide plans and prices, set each plan's features and limits in Admin → Pricing (the form now edits alerts, AI analyses and Ask Helix limits too), create the matching Whop plans, then set `WHOP_PLAN_MAP`. Steps are in DEVELOPMENT.md "Whop billing".
