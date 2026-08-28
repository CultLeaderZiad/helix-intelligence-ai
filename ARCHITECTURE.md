# Architecture

## 1. What Helix is

Helix Intelligence is organized around four "loops," each its own route
under the sidebar:

| Loop | Route | Status | What it does |
|---|---|---|---|
| Discover | `/discover` | **Live** | Query competitor ad libraries, run an async scrape job, browse/filter/sort the resulting creatives, inspect one in detail |
| Intelligence | `/intelligence` | PLANNED | Mine recurring creative patterns across a discovered corpus |
| Create | `/create` | **Live** | Draft new creative briefed on the patterns that win, using Higgsfield media generation via webhook/polling |
| Performance | `/performance` | PLANNED | Feed live performance data back into the scoring model |

The single source of truth for this list is `src/app/navigation.js`
(`NAV_SECTIONS`). The sidebar, the `⌘K` command palette, and the document
`<title>` all derive from it, and routes are generated from it in
`src/App.jsx` — a loop cannot appear in one navigation surface and be
missing from another. Loops with `status: "pending"` render
`PendingLoopPage`, an honest "not wired up yet" screen, instead of a route
that 404s or a screen faking data.

## 2. Frontend stack

- **Vite 7** — build tool and dev server. Not Next.js; there is no
  server runtime in this repo.
- **React 19**, function components and hooks only.
- **react-router-dom 7** — `BrowserRouter` in `src/main.jsx`, route table
  in `src/App.jsx`.
- **Tailwind CSS v4** — configured via `@tailwindcss/vite`. There is no
  `tailwind.config.js`; all theme tokens live in `src/styles/globals.css`
  inside `@theme { ... }` (Tailwind v4 CSS-first config).
- **@fontsource-variable/inter** and **@fontsource-variable/jetbrains-mono**
  — self-hosted variable fonts, no external font requests.
- **lucide-react** — the only icon set. No emoji, no custom SVG icon set.
- **clsx** + **tailwind-merge** (wrapped as `cn()` in `src/lib/utils.js`) —
  the only className composition utility used anywhere in the app.
- No state management library, no data-fetching library (no SWR/React
  Query/Redux). See §4 — the app has one data boundary and a single
  purpose-built async hook per feature.
- No test runner is currently configured.

## 3. Project structure

```
src/
  app/                 Shell chrome — not routed pages
    AppShell.jsx         Fixed rail + scrollable workspace + status strip
    Sidebar.jsx           Primary nav (desktop rail / mobile overlay)
    StatusBar.jsx         Bottom instrument strip (telemetry readout)
    BreadcrumbBar.jsx     Per-page top strip (trail + meta + actions)
    CommandBar.jsx        ⌘K command palette
    TelemetryContext.jsx  Shell-level telemetry the pages report into
    navigation.js         NAV_SECTIONS — single source of truth for routes

  pages/               Routed top-level screens
    DiscoverPage.jsx       Composition root for the Discover loop
    PendingLoopPage.jsx    Placeholder for Intelligence/Create/Performance
    NotFoundPage.jsx       404

  features/discover/   Discover-loop presentational components
    SearchQueryBar.jsx, FilterRail.jsx, JobProgress.jsx,
    ResultSummary.jsx, ResultsTable.jsx, CreativeDetailPanel.jsx

  components/ui/       Generic, feature-agnostic UI primitives
    Button.jsx, Field.jsx (Label/Input/Select/Checkbox), KeyHint.jsx,
    Metric.jsx (MetricValue/ScoreBar/StatBlock), Panel.jsx,
    ProgressBar.jsx, States.jsx (Skeleton/SkeletonRows/EmptyState/ErrorState), Tag.jsx

  hooks/
    useDiscoverySearch.js  Owns the Discover async job lifecycle (see §4)
    useAsync.js            Minimal generic async-state hook (data/error/loading)
    useMediaQuery.js       useIsMobile / useIsBelowLg / useIsBelowXl

  services/            The data boundary (see API_CONTRACTS.md)
    index.js             Picks mock vs. api per domain, exported as the only import surface
    config.js            DATA_SOURCE / API_BASE_URL / mock latency & failure knobs
    contracts.js          JSDoc-only typedefs — the agreed shape client ⇄ backend
    http.js               fetch wrapper + ServiceError, used only by api/*
    api/                  Thin FastAPI-shaped implementations (not wired up yet)
    mock/                 In-memory implementations backed by src/data/*

  data/                Fixtures. Only ever imported by services/mock/*
    creatives.js, brands.js, patterns.js, insights.js, jobs.js

  lib/                 Pure functions, no React, no service imports
    format.js  Every numeric/date readout in the UI routes through here
    score.js   Score tier → Tailwind class mapping (accent threshold logic)
    insight.js "Why this ad matters" derivation from real creative fields
    constants.js  Enumerations mirrored from the (future) FastAPI schema
    utils.js  cn() className helper

  styles/globals.css   Design tokens (see DESIGN_SYSTEM.md)
  App.jsx, main.jsx     Root component and entry point
```

## 4. Component architecture — the page → hook → service contract

This is the one architectural rule that must not be violated when
extending Discover or building a new loop:

```
Page (composition root)
  owns UI intent: query text, staged filters, sort, selection
  │
  ▼
Feature hook (e.g. useDiscoverySearch)
  the ONLY thing that talks to a service
  owns async lifecycle state: phase, job, results, error
  │
  ▼
services/index.js
  the ONLY module that knows whether data is mocked or real
  │
  ▼
services/mock/*.mock.js   OR   services/api/*.api.js
  (selected per-domain by DATA_SOURCE, see API_CONTRACTS.md)
```

Concretely, for Discover:

- **`DiscoverPage.jsx`** is the composition root. It holds `query`,
  `draftFilters` / `appliedFilters`, `sort`, `filtersOpen`, `selectedId`
  as local state, and renders the presentational components in
  `features/discover/`, passing them props and callbacks. It does not
  call a service directly.
- **`useDiscoverySearch.js`** is the *only* hook Discover components use
  to reach data. It owns `phase` (`idle | submitting | running |
  fetching_results | ready | error`), `job`, `results`, `error`, and
  exposes `submit / refine / cancel / retry`. It polls
  `discoverService.getJobStatus()` on an interval and stops when the job
  settles. Every value the `JobProgress` UI renders (stage, records
  found, elapsed ms) is application state returned by this hook — never
  a CSS animation standing in for progress.
- **`CreativeDetailPanel.jsx`** additionally uses the generic
  **`useAsync.js`** hook to call `creativeService.getCreativeById()` —
  a synchronous-shaped read, not a job. It is not routed through
  `useDiscoverySearch` because it's a different service domain
  (creatives vs. discovery jobs).
- **No component in `features/discover/` or `pages/` imports from
  `services/mock`, `services/api`, or `src/data` directly.** They only
  ever import `discoverService` / `creativeService` / `analysisService`
  from `@/services`, or — more commonly — only receive already-fetched
  data as props from a hook.

**Why this matters for future work:** when Intelligence/Create/Performance
get built, or when Discover grows new capability, follow the same shape —
a page owns intent, a dedicated hook owns the async lifecycle for one
service domain, and the hook is the only caller of `@/services`. This is
what lets the FastAPI cutover (see `API_CONTRACTS.md`) touch zero
component code.

One documented, deliberate exception: `ResultsTable.jsx` and
`JobProgress.jsx` import `brandsById` (from `@/data/brands`) and
`DISCOVERY_STAGES` (from `@/data/jobs`) directly. These are not row data —
`brandsById` resolves a display name the list endpoint doesn't embed, and
`DISCOVERY_STAGES` is shared pipeline vocabulary the real worker will
report against with the same keys. Both imports disappear the moment the
corresponding endpoint embeds/returns that data; nothing else about the
component changes.

## 5. Data models

Canonical shapes live as JSDoc typedefs in `src/services/contracts.js`
(no runtime code — types only, so editors get intellisense without
TypeScript). Every mock and every future HTTP implementation must satisfy
these shapes exactly.

- **`Creative`** — `id`, `brand_id`, `platform`, `format`, `headline`,
  `body`, `cta`, `landing_domain`, `thumbnail_ratio`, `duration_seconds`,
  `first_seen`/`last_seen` (ISO-8601), `days_active`, `variant_count`,
  `scores: Scores`, `metrics: CreativeMetrics`, `pattern_ids: string[]`.
- **`Scores`** — `hook | clarity | retention | composite`, each
  `number | null`. `null` means "not scored," a real and expected state,
  not an error.
- **`CreativeMetrics`** — `impressions_est`, `spend_band` (`low | mid |
  high | very_high | null`), `engagement_rate`, `ctr_est`.
- **`Brand`** — `id`, `name`, `domain`, `category`, `ad_count`,
  `first_seen`.
- **`Pattern`** — `id`, `label`, `family`, `prevalence` (0–1),
  `lift_index`.
- **`Insight`** — `id`, `creative_id`, `kind` (`hook_analysis | risk |
  opportunity`), `title`, `summary`, `confidence`, evidence
  (`evidence_creative_ids`), `generated_at`, `model_version`. Insights
  always carry provenance and a confidence value — never a bare string —
  so the UI can attribute the claim.
- **`Job`** — the async work handle every long-running operation returns
  immediately (discovery scrapes today; batch scoring/generation in
  future loops): `job_id`, `status` (`queued | running | succeeded |
  failed`), `progress` (0–1), `stage`/`stage_label`/`stage_index`/
  `stages_total`, `records_found`, `elapsed_ms`, timestamps, `error`.
- **`Paginated<T>`** — the envelope every list/collection endpoint
  returns: `items`, `total`, `page`, `page_size`, `has_more`,
  optional `took_ms`. No endpoint returns a bare array.
- **`SearchParams`** — `query`, `filters` (`platforms`, `formats`,
  `spend_bands`, `min_score`, `min_days_active`), `sort`, `page`,
  `page_size`.

Conventions, chosen to match FastAPI + Pydantic defaults, and binding for
any new model added later: **snake_case keys**, **ISO-8601 UTC
timestamps**, **pagination envelope for every list**, **long work
returns a Job, never a blocking response**.

Fixture data satisfying these shapes lives in `src/data/*.js` and is
deliberately imperfect: a minority of records have null/missing fields
(no thumbnail ratio, no engagement rate, unscored composite) so the UI is
forced to handle real-world gaps from day one, not just the happy path.

## 6. Mock service interfaces

See [`API_CONTRACTS.md`](./API_CONTRACTS.md) for the full contract,
endpoint mapping, and the mock ⇄ API parity guarantee.

## 7. Current Discover flow

1. User types a query and/or opens `FilterRail` and stages filter changes
   (staged, not live — editing the rail never fires a job; `FilterRail`
   receives `dirty` and says so).
2. User clicks **Run discovery** (or presses Enter in the query field).
   `DiscoverPage.runDiscovery()` snapshots `draftFilters` into
   `appliedFilters` and calls `useDiscoverySearch().submit()`.
3. `submit()` calls `discoverService.search()`, which returns a `Job`
   immediately (`status: "queued"` → `"running"`).
4. The hook polls `discoverService.getJobStatus(jobId)` every
   `JOB_POLL_INTERVAL_MS` (400ms) and updates `job` state each tick.
   `JobProgress.jsx` renders this as a terminal-style stage transcript
   driven entirely by `job.stage_index` / `job.records_found` /
   `job.elapsed_ms` — nothing here is a CSS-only animation.
5. On `status === "succeeded"`, the hook calls
   `discoverService.getJobResults(jobId, { page: 1, sort })` and moves to
   `phase: "ready"`.
6. `ResultsTable.jsx` renders the page of `Creative` rows; selecting one
   sets `selectedId`, which mounts `CreativeDetailPanel.jsx`. That panel
   calls `creativeService.getCreativeById(id)` — a separate call from the
   list, because the detail endpoint hydrates `brand` and `patterns`
   relations the list endpoint deliberately omits.
7. Changing `sort` while `phase === "ready"` calls `refine()`, which
   re-fetches results for the *same* job — it does not re-run the scrape.
8. On `status === "failed"`, the hook sets `phase: "error"` and
   `JobProgress` renders the failed stage inline; `retry()` resubmits the
   last params.

## 8. Current Create flow (Higgsfield Integration)

1. User selects a Source Creative (from Discover) or provides a custom brief.
2. The UI drafts a `CreativeBrief` using the AI Router (falling back across Groq, OpenRouter, Gemini, AIHubMix, Token Harbor).
3. The user initiates generation by selecting a media capability (e.g., `IMAGE_FAST`).
4. The `mediaService.generateMedia` call creates a `MediaGenerationJob` in the backend.
5. The backend (`HiggsfieldProvider`) submits a generation request to the Higgsfield API. It includes a `webhook` payload pointing to the backend's `/api/v1/webhooks/higgsfield` endpoint.
6. The frontend uses `useMediaGeneration` to poll `mediaService.getJobStatus(jobId)` while waiting.
7. Higgsfield processes the request. Upon completion (success or failure), it POSTs to the webhook endpoint.
8. The backend's webhook handler dedupes the event, updates the job status, and if successful, downloads the generated artifact to persistent storage.
9. The polling frontend receives the updated status (`succeeded`) and artifact URL, rendering the result with full lineage intact.

## 9. Future FastAPI integration — PLANNED

Not implemented. When it happens:

- Set `VITE_DATA_SOURCE=api` and `VITE_API_BASE_URL=<backend origin>`.
- `src/services/index.js` switches every domain's service from
  `services/mock/*.mock.js` to `services/api/*.api.js` — this is the
  entire cutover. No component, hook, or page changes.
- The `api/*.api.js` files already exist and are written against the
  contracts in `contracts.js`; they call `request()` from `services/http.js`,
  which throws a normalized `ServiceError` on failure so error-handling
  code never branches on data source.
- Expected endpoints are documented as comments at the top of each
  `api/*.api.js` file (e.g. `POST /v1/discovery/jobs`,
  `GET /v1/creatives/{id}`). See `API_CONTRACTS.md` for the full list.

## 10. Future Neon database integration — PLANNED

Not implemented, and nothing in this repository talks to a database.
When a backend is built, the FastAPI service is expected to be backed by
Neon Postgres; the frontend has no direct database dependency in any
scenario — it only ever talks to the HTTP contract in `contracts.js`.
This frontend repo requires no changes for that integration beyond the
`VITE_DATA_SOURCE` / `VITE_API_BASE_URL` cutover in §9.

## 11–14. Design tokens, motion rules, anti-patterns

See [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md).

## 15–16. Running, building, TODOs

See [`DEVELOPMENT.md`](./DEVELOPMENT.md).
