# Architecture

## 1. What Helix is

Helix Intelligence has three features, each its own route:

| Feature | Route | Status | What it does |
|---|---|---|---|
| Discover | `/discover` | **Live** | Query competitor ad libraries through a durable background job, browse/filter/sort the resulting creatives, inspect one in detail |
| Monitors | `/monitors` | Per-workspace flag `monitors` | Re-run a saved search on a schedule and report what changed |
| Boards | `/swipe-files` | Per-workspace flag `swipe_files` | Save creatives into boards and create a report link |

The navigation list lives in `src/app/navigation.js` (`NAV_SECTIONS`); the
sidebar and the `⌘K` palette derive from it through `visibleSections(flags)`.
Monitors and Boards appear when the workspace is granted `monitors` /
`swipe_files` (the same flags the API enforces with `require_feature`);
otherwise their routes redirect to `/discover`. Team and the experimental
admin pages still need `VITE_ENABLE_EXPERIMENTAL_FEATURES=true`.

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
    index.js             The only import surface; every domain uses its api/* client
    config.js            API_BASE_URL and job polling limits
    contracts.js          JSDoc-only typedefs — the agreed shape client ⇄ backend
    http.js               fetch wrapper + ServiceError, used only by api/*
    api/                  FastAPI clients (there is no mock or fixture data source)

  lib/                 Pure functions, no React, no service imports
    format.js  Every numeric/date readout in the UI routes through here
    score.js   Score tier → Tailwind class mapping (accent threshold logic)
    insight.js "Why this ad matters" derivation from real creative fields
    constants.js  Enumerations mirrored from the (future) FastAPI schema
    utils.js  cn() className helper

  styles/globals.css   Design tokens (CSS custom properties + Tailwind theme)
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
  the only import surface for data
  │
  ▼
services/api/*.api.js
  FastAPI clients (see API_CONTRACTS.md)
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
  `services/api` directly.** They only
  ever import `discoverService` / `creativeService` / `analysisService`
  from `@/services`, or — more commonly — only receive already-fetched
  data as props from a hook.

**Why this matters for future work:** when Discover grows new capability
or a new feature is built, follow the same shape —
a page owns intent, a dedicated hook owns the async lifecycle for one
service domain, and the hook is the only caller of `@/services`. This is
what lets the FastAPI cutover (see `API_CONTRACTS.md`) touch zero
component code.

## 5. Data models

Canonical shapes live as JSDoc typedefs in `src/services/contracts.js`
(no runtime code — types only, so editors get intellisense without
TypeScript). Every API client must satisfy these shapes exactly.

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

## 6. Service interfaces

See [`API_CONTRACTS.md`](./API_CONTRACTS.md) for the full contract and
endpoint mapping.

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

## 9. Backend integration

Every service talks to the FastAPI backend through `services/api/*.api.js`
and `request()` in `services/http.js`, which throws a normalized
`ServiceError` on failure. There is no mock data source: W8 removed the
in-memory mocks, the `src/data` fixtures, the `VITE_DATA_SOURCE` switch and
the backend `USE_MOCKS` flag. `VITE_API_BASE_URL` selects the backend origin
(same-origin `/api` proxy locally and in previews).

## 10. Database

The backend runs on Neon Postgres with row-level security. The API connects
as `helix_api_login` and the worker as `helix_worker_login`; see
`docs/w8/login-latency-and-production-db.md`. The frontend has no direct
database dependency.

## 11–14. Design tokens, motion rules, anti-patterns

Tokens live in `src/styles/globals.css`. There is no separate design-system
document yet.

## 15–16. Running, building, TODOs

See [`DEVELOPMENT.md`](./DEVELOPMENT.md).
