# AUDIT-W8 — Helix Intelligence, cut to the core

Branch `fix/core-W8` (stacked on W7, draft PR #31). Written 2026-11-05.

**How to read the status column.** Statuses come from what was actually run
in W8, not from reading code:

- **Verified**: run end to end during W8, in the browser or over HTTP,
  against the Neon dev branch `dev-w8`.
- **CI**: covered by the backend suite on PR #31 (Postgres 16, warnings are
  errors, zero skips enforced). All 8 CI jobs passed at `fc0d1aa`.
- **Partial**: some of it was run; the rest is noted.
- **Unverified**: code exists, but W8 did not run it (usually no provider key).
- **Fake / placeholder**: shows or returns data that is invented, or a stand-in.

Nothing in this document has been removed yet. **Section 8 is the list that
waits for the owner's OK.**

---

## 1. Summary

- The product surface is **50 frontend routes and 167 API endpoints across
  22 routers**, plus a worker that serves two unrelated products.
- Only the account platform (sign-up, sign-in, access request, admin
  approval, sign-out) was proven end to end in W8.
- **Discover, the foundation, has still never run a real search through the
  durable worker against a real provider.** That is the standing P0 from
  W5–W7. No provider key exists for a non-production environment.
- Roughly half the codebase serves features that are hidden behind
  `VITE_ENABLE_EXPERIMENTAL_FEATURES` (Create, Intelligence, Performance,
  Scout, Lead-gen, Swipe files, Team, API keys, Dashboard). They still ship,
  still have live API endpoints, and still cost maintenance.
- **Recommendation: keep 3 features.** Discover, Monitors, Saved boards with
  share (swipe files plus playbook links). Remove the rest. Section 7 has the
  reasons.

## 2. Feature inventory

### 2.1 Product features

| Feature | UI route(s) | API | Background | Status | Real user value today |
|---|---|---|---|---|---|
| **Discover** (ad library search) | `/discover` (live) | `/api/discovery/*` (5) | durable `work_items` outbox + worker, deadlines, fencing | **Partial.** Page loads, empty state is honest, server gates work. **No real search run**: no provider key (Adyntel, Apify, Meta, Bright Data) in any non-production environment. | Potentially high; unproven. Ranking uses a keyword rubric (§3.3). |
| **Monitors** (scheduled competitor watch) | `/monitors` (flag-gated) | `/api/monitors/*` (9) + cron `POST /monitors/tick` | `asyncio.create_task` per run in the **web process** | **Unverified.** Depends on Discover. Change-detection logic is careful (baseline run, empty-scrape refusal, miss threshold). | High once Discover works: this is the reason to return weekly. |
| **Swipe files / boards** | `/swipe-files` (flag-gated) | `/api/creatives/*` swipe endpoints | none | **Unverified** in W8. | Medium–high, cheap. The standard workflow of ad-research tools. |
| **Playbooks** (public share link) | `/playbook/:publicId` (public) | `/api/playbooks/*` (3) | none | **Unverified.** | Medium. A shareable deliverable for an agency's client. |
| **Intelligence** (pattern synthesis, AI insight) | `/intelligence` (flag-gated) | `/api/patterns`, `/api/insights`, `/api/brands` | LLM calls (Groq, OpenRouter, Gemini, AIHubMix, TokenHarbor fallback chain) | **Unverified.** No LLM key configured. | Low–medium. An LLM summary over a list. |
| **Create** (image/video generation) | `/create` (flag-gated) | `/api/media/*` (6) | in-process tasks; Gemini, Pollinations, AIHubMix | **Unverified.** | Low for an ad-*intelligence* product. Highest compute and credit cost. |
| **Performance / Audience simulation** | `/performance` (flag-gated) | `/api/simulation/*` (2) | LLM | **Fake / placeholder in substance.** An LLM *imagines* how audience segments react. Labelled `is_estimated`, but it is not measurement. | Negative: invented numbers that look like data. |
| **Dashboard** | `/dashboard` (flag-gated) | `/api/dashboard` (1) | none | **Unverified.** Aggregates `impressions_est` / `ctr_est` estimates. | Low. |
| **Scout: social handles** | `/scout/:mode` (flag-gated) | `/api/scout/*` (25) **and the same router again at `/api/v1/scout/*` (14)** | in-process tasks | **Unverified.** | A lead-generation product, not ad intelligence. |
| **Scout: Google Maps** | inside `/scout` | `/api/scout/maps/*` | in-process; `nominatim.openstreetmap.org` | **Unverified.** | Same as above. Scraping business contact data carries legal and ToS risk. |
| **Lead generation** (Scrapling) | `/scout/lead-generation` (flag-gated) | `/api/scout/leadgen/*` (11) | `workers/scrapling` (browser stack), `vendor/helix_scout`, `vendor/google_maps_scraper` | **Unverified.** Worker is off (`SCRAPLING_WORKER_ENABLED=false`). | Same as above. The heaviest dependency stack in the repo. |
| **Team / invites** | `/team`, `/team/accept` (flag-gated) | `/api/workspaces/*` (5), `/api/account/*` | none | **Unverified.** | Needed later for agencies; not for launch. |
| **API keys** | `/api-keys` (flag-gated) | `/api/account/api-keys*` | none | **Unverified.** | Low at launch. Table has no RLS (§5.2). |

### 2.2 Platform (infrastructure for any feature; not counted in the 3–5)

| Area | Routes / API | Status |
|---|---|---|
| Sign-up, sign-in, reload, sign-out (server revoke) | `/sign-up`, `/sign-in`; `/api/auth/*` (10) | **Verified** in the browser and over HTTP; **CI** (`test_w8_auth_flow.py`). |
| Access request → admin approve → approved state | `/access`; `/admin/access-requests`; `/api/account/access-requests`, `/api/admin/access-requests/*` | **Verified** in the browser. |
| Admin console | `/admin/*` (14 routes, 7 flag-gated); `/api/admin/*` (28) | **Partial.** Organizations list and access requests run. Users, audit log, support and updates not exercised. |
| Forgot / reset password | `/forgot-password`, `/reset-password` | **Unverified.** No mail provider; `AUTH_DEV_RESET_RETURN` is the stop-gap. |
| Notifications, updates banner | `/notifications`; `/api/notifications/*`, `/api/updates/*` | **Verified** (respond after login). |
| Support tickets | `/support`; `/api/support/*` (4) | **Unverified.** |
| Profile settings, avatar | `/settings`; `/api/account/*` | **CI** (W6 tests); not run in W8. |
| Public docs, legal | `/docs/*`, `/legal/*`, `/privacy`, `/terms`, `/cookies` | Loads (W7 route evidence). Content not reviewed line by line. |
| Health | `/health`, `/api/health/*` (4) | **Verified** (`/health` 200). Diagnostics behind `HEALTH_DIAGNOSTIC_KEY`. |
| Neon Auth webhook / JWKS | `POST /api/auth/webhook`; `NEON_*` settings | Legacy. Login no longer uses Neon Auth (DEVELOPMENT.md says so). |

### 2.3 Workers and jobs

| Job | Where it runs | Notes |
|---|---|---|
| Discover pipeline | durable `work_items` (outbox) claimed by `workers/scrapling/worker.py`; fallback `asyncio.create_task` in `discover_service.py:540` | Claims, leases, heartbeats, deadline, fencing (W5). One worker process serves **both** Discover and Lead-gen. |
| Lead-gen jobs | same worker (`_claim_next_job_async`) | Pulls Scrapling, Playwright, Patchright, Browserforge into the image. |
| Monitor runs | `asyncio.create_task(run_monitor(...))` in the **API process** (`monitor_service.py:370,402`) | Killed by any API restart or deploy; reconciled after 120 s of silence. |
| Media generation | `asyncio.create_task` in the API process (`media_service.py:393-395`) | Same restart exposure. |
| Welcome email | `asyncio.create_task` in `auth.py:156` | Fire-and-forget; lost on restart. |
| Trial reminders | `monitors.py:145` `_trial_reminders()` | A trial concept in a product with no trials (§3.1). |
| Job reconciliation | worker, at startup and every 60 s | Required. The API does not run it. |

## 3. AI slop

### 3.1 Trial and pricing leftovers (violates "no billing/pricing/trial UI")

- `src/components/ui/TrialBanner.jsx` (84 lines). Nothing imports it.
- `src/features/marketing/PricingSection.jsx`: the copy now reads "access by
  administrator", but the component is still `#pricing` on the landing page.
  Rename it or fold it into the hero.
- `src/pages/admin/SubscriptionsPlansPage.jsx` and the admin nav entry
  (flag-gated).
- Backend: `TRIAL_DAYS`, `TRIAL_IMAGES_PER_DAY`, `TRIAL_IMAGES_TOTAL`,
  `PAID_IMAGES_PER_DAY` settings; `plan_trial_default`; `trial_*`,
  `images_*`, `requires_plan` fields in every `SessionResponse`;
  `trial_expires_at`; 25.0 starting credits hardcoded in two places
  (`auth_service.py:155`, `billing_service.py:396`); `_trial_reminders()`.
- DEVELOPMENT.md: "Trial Defaults", "7-Day Trial & Gemini Image Generation",
  "Credit Cost Table". The table **contradicts the code**: docs say
  discover 2.0 / image 3.0 / video 8.0 / insight 1.0, while
  `billing_service.py:202-208` says 1.0 / 2.0 / 5.0 / 0.5.

### 3.2 Mock layer shipped to production

- `src/services/index.js` imports **every** `src/services/mock/*.mock.js`
  statically. With `VITE_DATA_SOURCE=api` they are dead code, but they are in
  the bundle.
- **Confirmed in a production build:** the entry chunk `index-*.js` (482 KB)
  contains the mock fixtures. That includes **real third-party businesses'
  contact details** (`riyadhsmile.com`, `drsulaimanalhabib.com`,
  `elitehospital.com.sa`) in `mapsScoutService.mock.js`, and fixture brands
  ("Northwind Supply") from `src/data/*.js` (105 records).
- `src/features/discover/ResultsTable.jsx:4,78` falls back to fixture brand
  names (`brandsById`) for real results. Real ids never match, so it is dead,
  but it pulls `src/data/brands.js` into Discover.
- `SignInPage.jsx:200-216` "Demo credentials" block (`admin@helix.io ·
  helix-admin`) is hidden in API mode, but it ships.
- Backend `USE_MOCKS` branches in auth, billing, discover, media, admin and
  dashboard. **Security risk: see §6.**

### 3.3 Scores that look like measurement

- Discover's default sort, **"Composite score"**, comes from a keyword rubric
  (`scraping/normalizer.py:144-170`): +4 if the headline contains
  "how/why/secret/never/stop/unlock/discover/reveal/?", +2 for any digit, +4
  if there is a CTA, +4 if it is a video, and so on.
- The detail panel discloses "A text rubric … not measured performance" (EN
  and AR), but the sort dropdown and table headers say "Composite score" and
  "Hook score" with no qualifier.
- `ctr_est` / `impressions_est` / "Est. impressions" sort: only Meta's
  `impressions.upper_bound` is real; other providers return `None`.
- Audience simulation: LLM-imagined reactions (see 2.1).

### 3.4 Dead and orphaned code

- Orphaned frontend files (no importer): `components/AdminBroadcastModal.jsx`
  (161), `components/ui/CardSwap.jsx` (382, **the only `gsap` user**),
  `components/ui/TrialBanner.jsx` (84), `features/scout/ScoutModeTabs.jsx`
  (88).
- `backend/app/services/media/modes.py:89` still maps
  `"higgsfield-ai/soul/v2/standard"`, although Higgsfield was removed in PR18.
- DEVELOPMENT.md §"Gemini Create Integration" documents
  `HF_API_KEY_ID/SECRET`, `Authorization: Key …`, `https://api.gemini.ai/…/soul/v2`.
  **No code reads any of that.** It is the Higgsfield doc after a
  find-and-replace, and it describes an API that does not exist.
- README says every unbuilt loop "points at a placeholder screen
  (`PendingLoopPage`)". Since W5 they redirect to `/discover`.
- README links `DESIGN_SYSTEM.md`, **which does not exist**. The anti-pattern
  list the brief asks to respect is missing.
- Router `scout` is mounted twice (`/api/scout` and `/api/v1/scout`).

### 3.5 Repository junk (tracked in git)

| Path | What |
|---|---|
| `dist/` (22 files) | Build output committed to git |
| `helix-audit/` (27 files, 928 KB) | An older audit export |
| `docs/w5`, `docs/w6`, `docs/w7` (87 files) | Per-wave evidence JSON. Useful history, but it is most of `docs/` |
| `backend/uploads/*.jpg` (3) | Generated or uploaded media committed to git |
| `login_before_click.png`, `login_after_click.png`, `e2e_live_test.cjs`, `test_cors.py`, `test_render.py`, `updates.md`, `antigravity-helix-remediation-prompt.md`, `skills-lock.json` | One-off scripts, screenshots and agent prompts at the repo root |
| `backend/create_tables.py`, `backend/metapi_dict_sample.json` | Superseded by Alembic, and a sample payload |

## 4. Hardcoded values

| Kind | Where | Recommendation |
|---|---|---|
| Credit costs | `billing_service.py:202-208`, `scout.py:113,451` (inline formulas) | One table in config or DB. Fix the doc mismatch. |
| Starting credits `25.0` | `auth_service.py:155`, `billing_service.py:396` | Config. Or drop with the trial model, since access is admin-granted. |
| Model names | `groq_provider.py` (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`), `gemini_provider.py` (`gemini-2.0-flash-lite-preview-02-05`, a dated *preview* model, also in `CreatePage.jsx`), `entity_intelligence.py`, `query_translator.py`, `creative_service.py`, `aihubmix_image_provider.py` (`gpt-image-2-free`), frontend `CreatePage.jsx`, `ApiKeysPage.jsx`, `contracts.js` | All in settings, defaulted once. The frontend should not name models at all. |
| Provider base URLs | `api.groq.com`, `generativelanguage.googleapis.com`, `api.metapi.io`, `api.adyntel.com`, `v2-api.scrapegraphai.com`, `gen.pollinations.ai`, `image.pollinations.ai`, `aihubmix.com`, `tokenharbor.ai`, `openrouter.ai`, `nominatim.openstreetmap.org` | Acceptable as defaults in one provider module. Several belong to features proposed for removal. |
| Contact email | `maps_scout_service.py`: `info@helixintelligence.ai` (Nominatim user agent) | Config. Goes with Scout if Scout is cut. |
| Placeholder copy with personal handles | `features/scout/HandleInput.jsx:75` (`softcodedevelop.com`, `cultleaderziad`) | Generic example. Goes with Scout. |
| `docs.helix.io` | `UpdatesPage.jsx:611`, `adminMessages.js:215` (placeholder text) | Not a real domain of this product. Use a relative example. |
| Limits | `AUTH_RATE_LIMIT` default 30 in code vs 10 in `.env.example`; `MONITOR_*`, `SCRAPLING_*`, `WORK_LEASE_S` | Already env-driven. Align defaults with `.env.example`. |
| Production URLs in docs | `helix-intelligence-ai.onrender.com`, `helix-intelligence-ai-six.vercel.app` in DEVELOPMENT.md | Fine in docs; keep out of code. |

## 5. Dependencies

### 5.1 Frontend (`package.json`)

| Package | Used by | Verdict |
|---|---|---|
| react, react-dom, react-router-dom, lucide-react, clsx, tailwind-merge | app-wide | keep |
| @fontsource-variable/inter, …/jetbrains-mono | `globals.css` | keep (fonts are 130 KB of assets; consider subsetting Latin+Arabic only) |
| driver.js | `app/OnboardingTour.jsx` | keep (onboarding tour, EN and AR) |
| **gsap** | `components/ui/CardSwap.jsx` only, **which nothing imports** | **remove** (with CardSwap) |
| **@testing-library/jest-dom** | no imports, not in vitest setup | **remove** |
| **@testing-library/user-event** | no imports | **remove** |
| **@types/punycode** | no imports | **remove** |
| playwright | `scripts/run_axe_audit.js`, `scripts/test_keyboard_forms.js`, root `e2e_live_test.cjs` | keep only if those scripts stay; they are not in CI. Heavy install. |
| vite, @vitejs/plugin-react, tailwindcss, @tailwindcss/vite, eslint, @eslint/js, eslint-plugin-react, typescript, @types/*, vitest, @testing-library/react, jsdom | tooling | keep |

Bundle (production build in W8): entry chunk **482 KB** (includes the mock
layer and fixtures); total JS 1.43 MB across chunks. Removing the mock layer
and the cut features is the main lever.

### 5.2 Backend (`backend/requirements.txt`)

| Package | Verdict |
|---|---|
| fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic[email], pydantic-settings, httpx, python-dotenv, python-multipart (avatar upload) | keep |
| **python-jose[cryptography]** | Replace with **PyJWT** (python-jose is effectively unmaintained). Used in one module. |
| bcrypt | Keep **only** while legacy `$2b$` hashes exist. Re-hash to PBKDF2 on next login, then drop. |
| boto3 | Keep while R2 is used (avatars, media). Heavy for a few S3 calls; if Create is cut, signed `httpx` PUTs to R2 can replace it. |
| Pillow | keep (avatar processing) |
| **aiosqlite** | **test-only** → move to a dev/test requirements file |
| *(not listed)* pytest, pytest-asyncio, pyflakes | Installed ad hoc in CI. Add `requirements-dev.txt`. |
| Worker: scrapling[fetchers], playwright, patchright, browserforge | **Remove with Lead-gen.** Discover's worker does not need a browser. |

## 6. Security

| # | Finding | Severity | Notes |
|---|---|---|---|
| S1 | **`USE_MOCKS=true` is an authentication bypass outside production.** Any password signs in; an email containing "admin" gets an **admin** token (`auth_service.py:48-49`). Production refuses the flag at boot; **staging, preview and test do not.** | **High** for any shared non-prod environment | Delete `USE_MOCKS` entirely. |
| S2 | `api_keys` has `org_id`/`user_id` but **no RLS policy** (not in any `ENABLE ROW LEVEL SECURITY` or policy migration) | Medium | App-level filters only. Add a policy, or cut API keys. |
| S3 | Sign-up revealed whether an email was registered ("An account with this email already exists") | Medium | **Fixed in W8:** sign-up now answers `202` with the same body, no token, and the same hashing work for new and existing emails; the client then signs in. Residual: sign-up followed by sign-in can still infer an existing account; closing that needs email verification (no mail provider yet). |
| S4 | ~~No server-side minimum password length~~ **Audit error.** `UserCreate`, `PasswordResetConfirm` and the profile password change already enforce 8–128 characters in Pydantic; the first pass searched only routers and services. | — | W8 adds a regression test (422 for too short and too long). |
| S5 | Access token lives in `localStorage` (`helix_access_token`) for **8 days** | Medium | An XSS hit means an 8-day session theft. Shorten it plus add refresh, or move to an `HttpOnly` cookie. Sign-out does revoke server-side (verified). |
| S6 | Rate limiter is in-memory per process and failed open on any internal error; state resets on restart; not shared across instances | Medium | **Partly fixed in W8:** `/api/auth/*` now fails closed (503) on a limiter fault. Still per-process; move to a Postgres or Redis counter when more than one instance runs. |
| S7 | Neon Auth webhook and JWKS still accepted (`POST /api/auth/webhook`, `NEON_*`) although login no longer uses Neon Auth | Low–Medium | Remove the unused auth path. |
| S8 | `AUTH_DEV_RESET_RETURN` returns reset links in API responses when on (refused in production) | Low | Remove once email is configured. |
| S9 | Scraping real businesses' contact details (Maps Scout, Lead-gen); real clinic contacts committed in mocks | Legal / ToS | Cut with Scout. |
| — | CORS, URL targets, DB target: fail closed (W7, plus the W8 allowlist). RLS deny-by-default with restricted login roles: **CI** and verified on dev-w8 as `helix_api_login`. Secret scan (gitleaks) on PRs: CI. Production refuses local-disk media and the owner DB role. | OK | |

## 7. Backend and database health

- **Migrations vs models:** dev-w8 migrated `c4d92e1f7a8b → d1f9c4a7b263`;
  `alembic check` reports **no drift**. CI also runs upgrade → downgrade -1 →
  upgrade on PR #31.
- **RLS:** tenant tables are covered directly or through parent policies,
  except `api_keys` (S2). `users`, `plans`, `app_updates` and
  `webhook_events` are global by design.
- **Missing indexes:** 78 tenant, foreign-key or status columns have no
  leading index. The one on **every request** is **`organizations.owner_id`**,
  used by the org lookup and the RLS policy. Next: `monitors(org_id)`,
  `monitor_runs(monitor_id)`, `media_jobs(org_id)`, `leadgen_jobs(org_id)`,
  `scout_jobs(org_id)`, `credit_ledger(job_id)`, `credit_reservations(user_id)`.
  Many vanish with the cut tables.
- **Jobs in the web process:** monitors, media, welcome email and the Discover
  fallback use `asyncio.create_task` in the API. Any deploy kills them;
  reconciliation cleans up after 120 s.
- **Rate limiter:** S6.
- **Storage:** production refuses local disk (good). Locally, media falls back
  to `backend/uploads/`, and three such files are committed.
- **Observability:** structured `log_event` JSON with request ids. **No error
  tracker (no Sentry)**, no metrics. W8 adds opt-in `Server-Timing`.
- **Login latency (Phase 1):** sign-in 28 → 10 SQL statements, warm
  ~5.5 s → ~2.0 s at 150 ms RTT. The remaining cost is round trips × RTT;
  co-locating Render with Neon (us-east-2) is the biggest remaining lever.
  See `docs/w8/login-latency-and-production-db.md`.
- **Error handling:** routes log and convert to structured 4xx/5xx; a global
  middleware returns `internal_error` with a request id. A few routes catch
  bare `Exception` and continue (for example the session builder swallowing
  org lookup errors into `pending`), which hides real failures.

## 8. Proposal — keep 3, cut the rest (**awaiting owner OK**)

### 8.1 Keep

1. **Discover**: the foundation, and the only thing every other feature
   builds on. Ship it with honest ranking:
   - default sort by days active or newest;
   - rename the rubric "Text rubric (0–10)";
   - only Meta's impression bounds shown as numbers.
2. **Monitors**: the retention and conversion driver. "Tell me when a
   competitor launches, kills or rewrites an ad" is why someone pays and comes
   back weekly. The change-detection rules are already conservative.
   - Move runs out of the web process into the worker.
3. **Boards and share**: swipe files (save Discover results into boards)
   plus a public read-only link (the playbook page, renamed "board link").
   - No AI.
   - Cheap to run.
   - Turns research into a deliverable an agency sends its client.

The platform pieces (auth, admin-granted access, admin console, support,
notifications, profile, docs, EN/AR) stay. They are infrastructure, not
features.

Optional 4th, **later**: Team accounts (agencies need seats). Keep it
flag-hidden, not deleted.

### 8.2 Planned removals

Nothing below has been done. Each line is one reviewable commit.

| # | Remove | Scope | Why |
|---|---|---|---|
| R1 | **Create** (media generation) | `/create`, `src/features/create/*`, `/api/media/*` generation, `media_service.py`, `services/ai/*image*`, `services/media/*`, Pollinations/AIHubMix/Gemini-image providers, media job tables (data kept until a drop migration is approved) | Not ad intelligence; highest cost; unverified |
| R2 | **Performance / audience simulation** | `/performance`, `simulation_service.py`, `/api/simulation/*`, `AudienceSimulationPanel`, `simulation_reports` | Invented numbers presented as analysis |
| R3 | **Dashboard** | `/dashboard`, `dashboard_service.py`, `/api/dashboard` | Aggregates estimates; no unique value |
| R4 | **Scout (social and Maps) and Lead-gen** | `/scout/*`, `/api/scout/*` and the duplicate `/api/v1/scout/*`, `/api/scout/leadgen/*`, `scout_service.py`, `maps_scout_service.py`, `leadgen_pipeline.py`, `scrapling_engine.py`, `atlas_pipeline.py`, `scrapegraph_lead_service.py`, `scout_parse.py`, `vendor/helix_scout`, `vendor/google_maps_scraper`, `app/data/leadgen_recipes`, scout/leadgen tables (data kept until a drop migration is approved). Worker keeps the Discover outbox loop only; drop Scrapling, Playwright, Patchright and Browserforge from its image. | A different product (lead-gen), legal risk, heaviest dependencies |
| R5 | **Intelligence** as a separate loop | `/intelligence` page, LLM fallback chain (Groq, OpenRouter, AIHubMix, TokenHarbor, Gemini text) | Low value now. A later "summarize this board" can come back as one call |
| R6 | **API keys** | `/api-keys`, key endpoints, `api_key_service.py` (or add RLS first) | Not needed at launch; S2 |
| R7 | **Trial, pricing and billing leftovers** | `TrialBanner.jsx`, `SubscriptionsPlansPage`, `_trial_reminders`, `TRIAL_*`/`PAID_*` settings, trial and images fields in `SessionResponse` (frontend updated together), `PricingSection` → merged into hero copy, DEVELOPMENT.md trial and credit sections | Standing rule: no billing, pricing or trial |
| R8 | **Mock layer and fixtures** | `src/services/mock/*`, `src/data/*`, `DATA_SOURCE` switch, demo credentials block, backend `USE_MOCKS` everywhere | S1; fake data in the production bundle |
| R9 | **Dead and orphaned code** | `AdminBroadcastModal.jsx`, `CardSwap.jsx`, `ScoutModeTabs.jsx`, Higgsfield mapping, Neon Auth webhook and JWKS path (S7), stale DEVELOPMENT.md Gemini/Higgsfield section | No callers |
| R10 | **Libraries** | npm: `gsap`, `@testing-library/jest-dom`, `@testing-library/user-event`, `@types/punycode` (+ `playwright` if its scripts go). pip: `aiosqlite` → dev file; worker browser stack (R4). Later: `python-jose` → PyJWT | Unused or tied to cut features |
| R11 | **Repository junk** | `dist/`, `helix-audit/`, `backend/uploads/*.jpg`, root screenshots, `e2e_live_test.cjs`, `test_cors.py`, `test_render.py`, `updates.md`, `antigravity-helix-remediation-prompt.md`, `skills-lock.json`, `backend/create_tables.py`, `backend/metapi_dict_sample.json`; add `dist/` to `.gitignore` | Not source |

Hidden behind a disabled flag rather than deleted: **Team** (optional 4th).

**Kept-feature fixes** (small; done with Phase 3, not removals):
- add the `organizations.owner_id` index;
- generic sign-up response (S3);
- rate limiter fails closed for auth (S6);
- honest Discover sort labels (§3.3);
- write the missing `DESIGN_SYSTEM.md`, or drop the link to it;
- fix README's `PendingLoopPage` claim.

Database tables for cut features are **not dropped** in this phase. Dropping
them needs a separate migration and the owner's yes, on a Neon branch first.

### 8.3 Branch cleanup (also awaiting OK)

23 remote branches exist. The stack (`fix/intelligence-W0…W7`,
`fix/core-W8`) and `main` stay. Candidates to delete **after** the stack
lands: `arena/01a070f8-helix-intelligence-ai`, `audit/helix-full` (PR #27,
docs-only), `dev`, `fix/latest-fixes`, `fix/no-hardcode-zero-errors`,
`hoplite/*` (6), `v0/*` (2). Nothing is deleted until the owner says which.

## 9. Production needs (unchanged by this audit)

See `docs/w8/login-latency-and-production-db.md`:
- migrations to `d1f9c4a7b263` over the direct host;
- `GRANT helix_app TO helix_api_login`, `GRANT helix_worker TO helix_worker_login`;
- API `DATABASE_URL` on `helix_api_login` (pooler, `sslmode=require`), worker on `helix_worker_login`;
- Render in the same region as Neon (us-east-2);
- an authorized **non-production provider key** to prove Discover end to end. Still the P0.
