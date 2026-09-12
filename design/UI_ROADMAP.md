# Helix — UI roadmap + PR #10 review

Companion to [`design/board.html`](board.html), which carries the visual before/after for every letter.
Measured against `main @ bea7ff2` (PR #10 merged) plus the `arena/*` Discover/billing fixes.

---

## 1. PR #10 — deep analysis

**State:** merged. 45 files, +1751/−329, 7 commits, one per fix group. It *is* HEAD, so the earlier
"Comprehensive Evidence-Based Audit" was written against this code plus a stale Render deployment.

### 1.1 Verified claims (spot-checked in HEAD, all true)

| PR claim | Evidence |
|---|---|
| `import os` restored in `groq_provider` / `openrouter_provider` | `head -1` of both files |
| Silent heuristic synthesizer removed | `grep -rn "heuristic" backend/app` → 0 matches |
| Reset tokens single-use, hashed, purpose-scoped, burned on bad guess | `auth_service.reset_password` + `security.decode_password_reset_token` |
| Duplicate concurrent searches structurally impossible | `main.py` partial unique index `uq_scrape_jobs_active_query` + `IntegrityError` race handler returning the winner pre-charge |
| Stuck jobs swept + refunded at boot | `main.py` lifespan reconcile block + per-job `refund()` |
| Client polling ceiling | `useDiscoverySearch` `JOB_POLL_TIMEOUT_MS` → `PHASE.TIMED_OUT` |
| Case-insensitive emails end to end | `func.lower` in `auth_service`, signup normalization, offline suite |
| Adyntel domain gate | `is_domain_shaped()` in chain *and* provider |
| Nested error boundaries | `ErrorBoundary` variants + outlet/panel wrapping |

### 1.2 What it left open (fix before design work)

**P0 — password-reset links are returned to the caller by default.**
`backend/app/core/config.py:21` → `AUTH_DEV_RESET_RETURN: bool = os.getenv("AUTH_DEV_RESET_RETURN", "True")`,
and `.env.example` ships `=true`. `render.yaml` has no `envVars` block, so unless the Render dashboard sets
`false`, `POST /api/auth/forgot-password {"email":"<any user>"}` responds with `reset_url` carrying a live
token, and `POST /api/auth/reset-password` returns a fresh session for that account — including admins.
Mitigation, in order of value:

1. Default the flag to `False`; only honour it when not production (`ENV`/`DEBUG` guard).
2. Rate-limit `forgot-password` (there is none today): e.g. 5/min/IP + 3/hour/address, 429 with a neutral body.
3. Stop logging the full reset URL at `WARNING` — Render log readers currently get takeovers too. Log the address only.
4. When a mail provider lands, delete the return path entirely rather than gating it.

**P0 — `POST /api/auth/webhook` is unauthenticated and self-approving.**
`routers/auth.py:194-215` computes `expected_signature`, **logs both the received and expected values, and never
compares them**; the endpoint then creates users (`password_hash="EXTERNAL_AUTH_MANAGED"`, 14-day trial) and an
org. Anyone can mint accounts with a longer trial than signup grants (14d vs 7d). Fix: `hmac.compare_digest`,
401 on mismatch or missing header, never log signature material, align the trial length, and gate the route off
entirely if the Neon/better-auth flow is dead — note `better-auth` is still a dependency in `package.json`.

**P2 — PBKDF2 in the event loop.** `get_password_hash` = 100 000 synchronous rounds called from async handlers
(sign-up, reset) and `verify_password` likewise; on Render's single worker that is a ~60–90 ms loop stall per
call and a cheap CPU-DoS amplifier. Use `starlette.concurrency.run_in_threadpool`, or switch to the
`passlib[bcrypt]` you already install.

**P2 — error surface.** `/auth/sign-in` returns `detail=f"…{type(e).__name__}: {e}"` and a 500 when a user
"found during auth" is missing on re-query — internal state and exception text to an anonymous client. Keep the
honest 503 shape PR #10 introduced elsewhere, log the detail server-side only.

**P1 — `GET /api/media/jobs/{job_id}` has no ownership check.** `media_service.get_media_job` selects by `id`
alone (line 295-300), while every other read in the app is scoped by `user_id`/`org_id`. Any signed-in user who
supplies another user's job id gets their prompt, `result_url`, `error_message` and `parameters` (which include
`credential_mode` and the resolved model). `POST /media/upload` is similarly unscoped for reads of stored bytes.
Fix: filter on `user_id == current_user.id OR org_id == user's org` and 404 otherwise — a job id is not a
capability. (Also worth noting `POST /media/jobs/{id}/cancel` returns a success envelope without cancelling
anything: `media_service` has no cancel path at all.)

**Sequels the PR body names, still open:** invalid production `HF_API_KEY_ID/SECRET`; template rows already in
Neon (guard only stops new contamination); tooltip sentences untranslated; balance lost-update on concurrent
charges of *different* queries (`UPDATE … WHERE credit_balance >= :amt`).

**Process note:** the audit reported uncommitted `src/pages/DashboardPage.jsx`, `src/services/api/dashboardService.api.js`,
`dist/index.html`. `DashboardPage.jsx` is in PR #10; the other two are not — at HEAD the barrel maps `dashboardApi`
→ `dashboardService` and both sides expose `getMetrics`, so nothing is dangling, but `dist/` committed into git
should be dropped (it is a build artifact and it will keep showing up as "dirty").

---

## 2. Recommendation

Ranked by **dependency order × current-state reality**, not preference. Your core loop is data-starved right now
(Apify unfunded, Meta `2332002`, Higgsfield keys invalid), so screens whose payoff is "look at my data" get judged
on an empty or thin corpus, while type size, feedback and empty states are what a tester meets in minute one.

| Order | Item | Effort | Why here |
|---|---|---|---|
| **-1** | PR #10 security tails (above) | ~1h | Live in prod; 30 min of work; protects everything you're about to build |
| **1** | **A1** type scale | 0.5–1d | Every other item lands on this scale; doing C1–C3 first means restyling twice |
| **2** | **A2** toasts | 0.5d | Answers "did that work?" *and* carries cost/refund; reuses 2 hand-rolled implementations |
| **3** | **B1** teaching empty states | 0.5d | The empty state is the product today; component already supports `action`/`size="lg"` |
| **4** | **C4** cost before action | 0.5d | Trust issue with a 402 at the end of it; smallest C with the widest effect |
| **5** | **A3** density toggle | 0.25d | Nearly free *after* A1 (token swap); wasteful before it |
| **6** | **C1 / C2 / C3** screen passes | 2–3d | One pass on the new scale; C1's premise is half-shipped (see below) |
| **7** | **D2** Arabic mechanism + drip | 1d + drip | 24/30 pages never call `t()`; translate per rewrite pass, not as a separate sweep |
| **8** | **B2** first-run checklist | 1d | Needs B1 so the steps point at self-explanatory states |
| **9** | **C5** admin DataTable | 1d | Real (0/9 paginated) but it's your surface, not the tester's |
| **10** | **D1** mobile/tablet | 2d | A workstation product; fund it only if testers really open it small |

**Do not** start with C1's score bars: `ScoreBar` already exists and is already used in `ResultsTable:132` and
`CreativeDetailPanel:317`. The Discover gaps are row typography, per-metric visibility, estimated-vs-reported
marking, and a results endpoint that ignores the filter rail. Rebuilding bars would be polishing what works and
leaving what lies.

---

## 3. Design spec — before / after, per letter

Visual mocks for all of these are in [`design/board.html`](board.html). Copy formula used everywhere:
**state → why → one action → what it costs → what happens if it fails.**

### A1 — Readability
- **Before:** 203 utilities at ≤11px (9px:9, 10px:92, 11px:102) vs 42 at 13px; `.label-mono` hard-coded 11px; Intelligence/Performance/Create/Dashboard 100% ≤11px; rows get 6px padding.
- **After:** `@theme` scale `--type-2xs 12 · xs 13 · sm 14 · md 15.5 · lg 19 · xl 24`; body 14/1.55; rule set = data→xs, copy→sm/md, labels→2xs mono, titles→lg; nothing under 12px; row padding 12–14px.
- **Files:** `src/styles/globals.css` + sweep across `src/pages/**`, `src/features/**`, `src/app/**`.
- **Guardrail:** CI grep gate failing on `text-[9px]|text-[10px]`.

### A2 — Toasts
- **Before:** local `const [toast, setToast]` + 4s timeout in `ApiKeysPage` and `SwipeFilesPage` only; elsewhere silent success and inline-text failure.
- **After:** `ToastProvider` in the shell + `useToast().push({intent,title,body,ttl,action})`, intents `ok|warn|err|bill` (bill always names the amount), portal stack bottom-right, `aria-live=polite`, max 3, ≥6s for errors, central `ServiceError` map (402 → ledger line, 403 → billing CTA).
- **First consumers:** key revoke/connect, save, copy, remix, ticket, plan edit — and job settle on Discover/Create/Intelligence (charged · refunded · timed out).

### A3 — Comfort / Compact density
- **Before:** one density, chosen for you; `size="lg"` opts are the only variation.
- **After:** `:root[data-density="comfort"|"compact"]` swapping `--type-*`, `--pad-row`, `--gap-panel`, `--rail`; toggle next to the language switcher, persisted per user; pages never take a `dense` prop.
- **Acceptance:** switching mid-task keeps scroll, selection and poll state; compact still floors at 11px.

### B1 — Teaching empty states
- **Before:** 8 `EmptyState` uses (7 already accept `action`) vs 21 raw "no data"/"NO DATA" strings; no price, no reason, no next step.
- **After:** `EmptyState` gains `cost`, `nextStep`, `footnote`, `tone="blocked"`; every data surface renders exactly one of skeleton · empty · blocked · error · rows; blocked variant reuses the backend's ledger copy ("Apify: HTTP 402 · Meta: 2332002 — 1.0 credit refunded").
- **Acceptance:** a new account reaches its first meaningful screen on every page from the empty state alone.

### B2 — First-run checklist
- **Before:** wizard modal + driver.js tour; `has_completed_onboarding` is binary, set by clicking through, unresumable, un-trusted.
- **After:** 4 steps derived from real rows (`scrape_jobs`, `ai_insights`, `media_jobs`, `saved_creatives`) behind one `GET /account/setup-state`; card in Dashboard + dismissible shell strip; "resume tour" jumps to the first incomplete step; completion sets the flag server-side.
- **Acceptance:** reload-safe progress; blocked/expired users see the blocker as step 0 rather than "go generate".

### C1 — Discover
- **Before:** table rows at 11px; composite bar only; filter rail at 10px with no counts; estimates indistinguishable from reported metrics; results endpoint ignores the rail.
- **After:** headline 15px / meta 12.5px, hook+clarity+composite as three bars, `≈ estimated` marker driven by `is_estimated`/`data_source` (both columns exist), chips with live counts labelled as *local* refinement until the endpoint takes filters.
- **Backend asks:** `GET /creatives` accepting `platform,min_days_active,spend_band,sort`; return the two provenance fields.

### C2 — Create
- **Before:** small corner preview, spinner, text history; *provider routing is already tiered* (`CreatePage.jsx:202` → `isTrial ? "gemini" : "higgsfield"`), so the "Higgsfield disconnected" audit item is stale.
- **After:** canvas-sized preview with aspect switch on the crop edge; stage rail bound to the real job statuses (`pending→running→in_progress→completed/failed`) with provider named; thumbnail gallery of the user's own jobs with prompt-on-hover and remix-with-params; failures show the red step + reason + "not charged".
- **Backend ask:** `GET /media/jobs?mine=1&limit=12` (no list endpoint exists), and expose `provider`,`error_message`,`cost`.

### C3 — Dashboard
- **Before:** column-name KPIs (`AVG COMPOSITE 6.4`, `RANKED BY 3`) with no baseline.
- **After:** sentence first ("You found 43 live ads across 3 brands this week — 12 more than last week"), KPI second with delta, computed "what to do next" (thinnest brand / highest-delta cohort / unscored creatives), `InfoTip` retained underneath.
- **Backend ask:** `?window=7d|30d` + previous-period value per metric so deltas aren't client-guessed.

### C4 — Billing / credits
- **Before:** zero cost visibility pre-action; the first price a tester sees is the 402. Numbers also drift in-code: `DISCOVER_SEARCH_CREDIT_COST = 1.0` while `trigger_search`'s comment says "2.0 Credits" (2.0 is `discover_deep_fallback`).
- **After:** cost suffix on the control ("Run search · 1.0 credit"), shared client map from one endpoint (never hard-coded labels), disabled-with-reason when `balance < cost`, balance meter with "≈7 more searches", confirm sheet only for the expensive actions.
- **Corrects the brief:** a standard Discover search is **1.0** credit, not 2.

### C5 — Admin
- **Before:** 9 tables in 9 dialects; 5 have search, **0 have pagination**, no empty state, unlogged row actions.
- **After:** one `<DataTable>` with URL-synced search/filter/sort/page (pasteable into Slack), 25-row pages + total count, every mutation confirm → toast → ledger row, ban = type-to-confirm.

### D1 — Mobile / tablet
- **Before:** `useIsBelowLg` in DiscoverPage only; `min-w-[720px]` tables; breakpoints thin (sm:63, md:46, lg:27).
- **After:** exactly two modes — `≥lg` rail+panels, `<lg` bottom tabs + bottom-sheet detail; card list replaces the wide table; the three funded flows are Discover→detail, Create, Billing/credits; admin below `lg` says "best on a larger screen" instead of half-breaking.

### D2 — Arabic / RTL
- **Before:** 105 EN keys, all 105 present in AR, `dir` switching works — but only **5 of 30 pages** import `useLanguage` (Discover, Intelligence, Performance, Dashboard, Swipe Files). Everything else, incl. all 9 admin pages and the 4 auth pages, is English-only. Geometry uses physical margins, so mirrored panes land half-flipped.
- **After:** mechanism first — physical→logical utility sweep with a CI gate, per-domain dictionary files, coverage check that counts literals rendered without `t()`, Latin digits in an LTR isolate with `tabular-nums`; then translate each page inside the pass that rewrites it (C1→Discover, C3→Dashboard…), auth/Create/Billing first.
- **Why not now:** translating before C1–C3 means translating twice; the CI floor means coverage still rises from day one.

---

## 4. Suggested slice boundaries (four PRs, each independently shippable)

1. `security: close reset + webhook exposure` — config default, rate limit, log hygiene, webhook HMAC compare, PBKDF2 off-loop.
2. `design: tokenized type scale + density tokens (A1, A3)` — includes the CI lint gate; no behaviour change.
3. `feedback: toast system + cost-before-action (A2, C4)` — deletes both local toasts; surfaces `CREDIT_COSTS` to the client.
4. `states: teaching empty + blocked variants (B1)` — 21 call sites, `tone="blocked"`, admin blocked-row parity.

B2, C1, C2, C3 then land on top of 2–4 without re-touching them; C5/D1/D2 follow per evidence.
