# Frontend route inventory (static audit)

> **Scope/status:** source-level inventory of the checked-out `audit/helix-full` worktree (HEAD `eab70cc`), compared with `main` commit `5b45806` where route wiring changed. No app files were edited. This is not a browser/runtime audit: parent-managed EN/AR screenshots and interaction checks are **pending**. Route definitions are in `src/App.jsx`; evidence and machine-readable route records are in [`evidence/frontend-routes.json`](evidence/frontend-routes.json).

## What this inventory means

`real` = code/content and a corresponding API service or static source exist; it does **not** prove a successful live request. `partial` = UI exists but the full user outcome, external provider, or live behavior is incomplete/unverified. `empty` = intended 404/empty state, not a product feature. `mock` = a mock adapter is selectable in development. `broken` and `dead` are reserved for directly evidenced non-working or unreachable code; this static pass does not label runtime behavior broken without browser evidence. Most data screens can use mock adapters when `VITE_DATA_SOURCE=mock`; production builds reject that source (`src/services/config.js`).

Audience shorthand: **Public** (no app session), **User** (authenticated workspace), **Admin** (admin role), **Invitee** (team acceptance flow).

## Public routes

Declaration evidence: `src/App.jsx:181-198`.

| Route | Purpose / key surface | Service or data path | Status / finding |
|---|---|---|---|
| `/` | Marketing landing, product loops, CTA; Public | Static React content; navigation to auth | `partial` — marketing surface only; not proof of the advertised workflows. |
| `/sign-in` | User sign-in form | `authService` → `/auth/sign-in`, `/auth/session` | `partial` — API wired; identity-provider/config and successful flow not runtime-verified. |
| `/sign-up` | Account registration | `authService` → `/auth/sign-up` | `partial` — same unverified auth/config dependency. |
| `/forgot-password` | Request reset link | `authService` → `/auth/forgot-password` | `partial` — delivery/provider not verified. |
| `/reset-password` | Set password from reset token | `authService` → `/auth/reset-password` | `partial` — valid-token and expired-token paths not browser-tested. |
| `/playbook/:publicId` | Public share view for a playbook | `playbookService` → `/playbooks/public/{id}` | `partial` — endpoint is wired; public record/auth behavior not live-tested. |
| `/updates` | Public published updates | `updatesService` → `/updates` | `partial` — API-backed, response state not live-tested. |
| `/legal` | Legal index | Static Legal page | `real` — same component as section routes. |
| `/legal/:section` | Sectioned legal content | Static Legal page | `partial` — dynamic section allowlist/fallback not browser-verified. |
| `/privacy` | Privacy content alias | Static Legal page | `real` — duplicate surface through `LegalPage`. |
| `/terms` | Terms content alias | Static Legal page | `real` — duplicate surface through `LegalPage`. |
| `/cookies` | Cookie content alias | Static Legal page | `real` — duplicate surface through `LegalPage`. |
| `/docs` | Documentation index | Static Markdown registry | `real` — populated from `src/features/docs/docsData.js`. |
| `/docs/scout-cli` | Dedicated Scout CLI reference | Static page | `real` — separate route from generic docs detail. |
| `/docs/:section` | First document in a documentation section | Static Markdown registry | `partial` — valid sections are `user-guide` and `api-reference`; unknown-section behavior not runtime-verified. |
| `/docs/:section/:slug` | Concrete documentation article | Static Markdown registry | `real` for registered article slugs; invalid slug behavior not runtime-verified. |

Registered article examples: `/docs/user-guide/{quickstart-account-and-trial,quickstart-first-search,quickstart-reading-intelligence,quickstart-remix-studio,quickstart-credits-and-limits,concept-how-discover-works,concept-scoring-system,concept-estimated-vs-real-data,concept-competitor-monitors,concept-audience-simulation,lead-generation,faq}` and `/docs/api-reference/{authentication,credit-costs-and-limits,endpoint-discover,endpoint-creatives,endpoint-media-generate,endpoint-monitors}`. These are static docs, not evidence that every described feature currently works.

## Authenticated workspace routes

Declaration evidence: `src/App.jsx:229-248`; all are inside `ProtectedRoute` and `AuthenticatedShell`.

| Route | Purpose / key surface | API/service path | Status / finding |
|---|---|---|---|
| `/discover` | Search, source resolution, results, filters; core loop | `useDiscoverySearch` → `discoverService`; `/discovery/jobs`, `/discovery/jobs/{id}`, `/discovery/jobs/{id}/results` | `partial` — real service path exists. The supplied audit brief reports production searches stuck at “resolving sources”; this was not reproduced here. |
| `/intelligence` | Creative analysis, patterns, insight and playbook views | `creativeService`, `analysisService`, `playbookService`; creatives, patterns, insights, playbooks | `partial` — feature wiring exists, but README/product state and navigation “live” labels conflict; no live data verified. |
| `/create` | Remix/media creation studio | `creativeService`, `useMediaGenerate` / `mediaService`; `/creatives/{id}`, `/media/jobs`, `/media/jobs/{id}` | `partial` — provider-backed generation path; Architecture calls Create live while README calls it planned. Output/provider not tested. |
| `/monitors` | Competitor monitor CRUD, run and event history | `useMonitors`, `monitorService`; `/monitors/`, `/monitors/{id}`, `/monitors/{id}/run`, `/monitors/events` | `real` (API wired; monitor service has no mock adapter); live persistence/alerts not verified. |
| `/scout` | Redirect to default social mode | `<Navigate to="/scout/social" replace>` | `real` redirect. |
| `/scout/lead-generation` | Lead-generation job workflow | `leadgenService`, `useLeadGenJob`; `/scout/leadgen/jobs`, `/scout/leadgen/jobs/{id}`, `/scout/leadgen/jobs/{id}/leads`, recipes/worker health | `partial` — external worker/runtime not verified; no mock adapter. |
| `/scout/:mode` (concrete intended values: `/scout/social`, `/scout/maps`) | Social-ad or Maps scouting | `scoutService` and `mapsScoutService`; `/scout/jobs...`, `/scout/maps/jobs...` | `partial` — social/maps mode UI and service paths exist. Arbitrary `:mode` values appear to fall back to a supported mode rather than a dedicated 404; runtime not checked. |
| `/performance` | Creative performance/scoring and monitor-assisted views | `creativeService`, `monitorService` | `partial` — page exists; docs call Performance planned and nav calls it live. No production performance data or scoring feedback loop verified. Declaration is relative (`path="performance"`, `src/App.jsx:238`), unlike adjacent absolute paths; React Router matching was not browser-tested. |
| `/dashboard` | Workspace metrics and playbook compilation | `dashboardService` → `/dashboard/metrics`; `playbookService` | `partial` — API wiring exists; declaration is relative (`src/App.jsx:239`); no live metrics verified. |
| `/swipe-files` | Saved/custom swipe-file creatives | `creativeService`, direct media upload via shared API client | `partial` — service path exists; upload and persisted list not tested. Secondary navigation, not one of six primary sections. |
| `/guide` | In-app guide/playbook content | Static guide surface | `real` content route; distinct from `/docs` and `/admin/guide`, so naming/navigation overlap is confusing. |
| `/billing` | Billing, usage and access lifecycle | `accountService` → `/account/billing`, `/account/usage/today`, `/account/access`, `/account/access-requests` | `partial` — UI supports manually granted access/request flows; no checkout/provider is present in the documented architecture. Do not present trial/plan copy as a purchasable subscription. |
| `/api-keys` | Workspace API keys | `accountService` → `/account/api-keys` plus workspace-provider request | `partial` — secret lifecycle and current provider wiring not verified. |
| `/team` | Team roster and invites | `accountService` → `/account/team`, `/account/team/invites`, `/account/team/members` | `partial` — API-backed; invite delivery/acceptance not browser-tested. |
| `/team/accept` | Accept a team invitation | `TeamAcceptPage`; account/team service | `partial` — invite-token states not runtime-tested. Invitee flow should remain reachable without confusing it with ordinary team navigation. |
| `/settings` | Profile/settings and avatar | `accountService` → `/account/profile`, `/account/avatar` | `partial` — API path exists; upload/session persistence not tested. |
| `/support` | User ticket list/detail/reply | `supportService` → `/support/tickets`, `/support/tickets/{id}`, `/support/tickets/{id}/reply` | `partial` — API-only service; response/empty/error states not live-tested. |
| `/notifications` | Notification inbox | `notificationService`, `updatesService`; `/notifications/`, `/notifications/{id}/read`, `/notifications/read-all`, published updates | `partial` — API-backed; has four filter controls (see tabs below). |

## Admin-only routes

Declaration evidence: `src/App.jsx:202-217`; the group requires `ProtectedRoute requireRole="admin"` and `AdminShellLayout`.

| Route | Purpose | API/service path | Status / finding |
|---|---|---|---|
| `/admin` | Operations overview | `adminService` → `/admin/overview/stats` | `real` (wired; data not live-verified). |
| `/admin/guide` | Operating playbook | Static `GuidePage` reuse | `real` content; overlaps user `/guide`. |
| `/admin/organizations` | Organization operations | `adminService` → `/admin/organizations` and organization actions | `partial` — API-backed admin actions, authorization and persistence not exercised. |
| `/admin/access-requests` | Review/grant/reject requests | `adminService` → `/admin/access-requests` | `partial` — route added vs `5b45806`; no admin session/browser test. |
| `/admin/subscriptions` | Plans/subscription administration | `adminService` → `/admin/plans` | `partial` — no payment processor documented; distinguish internal entitlements from billing. |
| `/admin/usage` | Usage and metering | `adminService` → `/admin/usage`, `/admin/usage/logs` | `partial` — response and tenant scoping not tested. |
| `/admin/feature-flags` | Feature-flag administration | `adminService` actions | `partial` — endpoint and enforcement behavior not tested. |
| `/admin/users` | User administration | `adminService` → `/admin/users` and user actions | `partial` — admin actions not tested. |
| `/admin/updates` | Announcement/banner editor and preview | `updatesService` → `/updates/admin`, `/updates/admin/all`, `/updates/banner`, `/updates/admin/{id}` | `partial` — editor/preview tabs; publish path not tested. |
| `/admin/support` | Support ticket queue | `adminService` → `/admin/support/tickets` | `partial` — API-backed; workflow untested. |
| `/admin/data-sources` | Provider/ingestion health | `adminService` → `/admin/system/health` | `partial` — “Probe All Sources” and failover labels are not proof of actual provider probes. Unmatched providers are rendered “Operational & Available in failover stack”; this fallback risks overstating health. `activeTab` is initialized but no corresponding tab controls/use were found. |
| `/admin/scrape-jobs` | Scrape job operations | `adminService` → `/admin/jobs` | `partial` — route present; controls/data not live-tested. |
| `/admin/health` | System health | `adminService` → `/admin/system/health` | `partial` — health response not verified. |
| `/admin/audit-log` | Administrative audit events | `adminService` | `partial` — endpoint wiring is present in service; tenant/audit completeness not checked. |

`AdminPendingPage` contains an explicit “not wired up yet” scaffold, but `rg` found no route importing it. Treat it as an orphan component, not proof that the listed admin routes are placeholders. `ADMIN_NAV_GROUPS` marks all admin destinations built; that label is not runtime evidence.

## Every discovered tab/filter control

This is the complete static search result for tab-state controls in pages; controls are buttons, and no `role="tab"` / `tablist` / `aria-selected` implementation was found in this scan. Confirm semantics and keyboard behavior in the managed Preview.

| Screen | Controls | Evidence | Notes |
|---|---|---|---|
| `/notifications` | All; Unread (count); Announcements; Alerts | `src/pages/NotificationsPage.jsx:170-181` | Filter states `all`, `unread`, `announcement`, `alert`; buttons, not ARIA tabs. |
| `/scout/social` and `/scout/maps` (admin only) | Active Workspace; Org Social Jobs (count); Org Maps Jobs (count) | `src/pages/ScoutPage.jsx:259-284` | Admin job queues only; choosing a job returns to current workspace. Mode is also URL-driven. |
| `/admin/updates` | Editor; Preview (Kie.ai Card Preview) | `src/pages/admin/UpdatesPage.jsx:484-513` | Local modal view switch; preview is a rendering preview, not published-state verification. |
| `/performance` | All Formats; video; image; day ranges 0, 7, 14, 30 | `src/pages/PerformancePage.jsx:137,434` and following filter controls | Filters, not tabs. |
| `/admin/data-sources` | No rendered tabs found | `src/pages/admin/DataSourcesPage.jsx:106` | `activeTab` state exists without setter/use; likely dead state, not a user-facing tab. |

Discover filter drawer and Scout Social/Maps mode switches are controls, not tablists; record them as interactions during screenshots. No further tab-state controls were found in the frontend page scan.

## Navigation, duplicate and orphan findings

- `src/app/navigation.js` exposes six primary sections and marks each `live`. `README.md` identifies Discover as the only end-to-end loop, while Intelligence/Performance are planned; `ARCHITECTURE.md` also conflicts with README about Create. Update badges/copy to reflect evidenced maturity, not route existence.
- The remaining workspace routes are secondary destinations (account menu, command bar, bell, or contextual links). `/dashboard`, `/guide`, `/swipe-files`, `/billing`, `/api-keys`, `/team`, `/settings`, `/support`, `/notifications`, `/team/accept` are not peers of the six primary loops. `/messages` is not declared; map any “Messages & Updates” label to `/notifications` explicitly or remove the label.
- `/guide` and `/admin/guide` reuse guide content with separate audiences; `/docs` is a different Markdown reference. Clarify labels to avoid three competing “guide/docs/playbook” entry points.
- `/legal`, `/legal/:section`, `/privacy`, `/terms`, and `/cookies` share `LegalPage`; keep one canonical content source and ensure aliases point to correct sections.
- `/scout` intentionally redirects; `/scout/:mode` is broad and can accept unsupported mode strings. Constrain mode values or render an explicit not-found state.
- Billing should retain honest usage/access-request information if needed, but hide trial countdowns, purchasable plan claims and checkout affordances until a payment provider and matching backend flow exist. The backend/docs describe manual admin-granted access and the UI has access requests; no checkout path is evidenced.
- The admin data-source fallback “Operational & Available in failover stack” is not grounded for unmatched provider IDs. Render “status unavailable” instead of green/operational language absent a source-specific health result.

## English/Arabic and RTL evidence

- `src/context/LanguageContext.jsx` owns EN/AR translations, reads `helix_lang`, and sets document `lang`/`dir`; `src/components/LanguageSwitcher.jsx` toggles the language. Global RTL support is implemented, but does not prove every component/layout has correct bidi behavior.
- Arabic literals are concentrated in `LanguageContext`, `LanguageSwitcher`, `ErrorBoundary`, and a portion of `IntelligencePage`; the other routes still contain English JSX literals/placeholders (notably Create, Monitors, Performance, Support, auth and admin). Thus the AR choice is not evidence of complete translation.
- Dynamic text has selective `dir="auto"` handling (including access-request, billing, guide, intelligence, and public-playbook content); this is not consistently applied across the entire app. Test mixed Arabic/Latin terms, URLs, numbers, forms, drawers, toast/error states and chart axes in Preview.
- Every route and tab needs EN and AR screenshots. Suggested capture key: `route-<slug>__<lang>.png`, with tab state suffix `__tab-<slug>`; **all proposed captures remain pending parent capture**. Do not treat these filenames as existing evidence.

## API wiring and trust boundaries

The service boundary is `src/services/index.js`; API implementations live in `src/services/api/`, mock counterparts in `src/services/mock/`. Default source is API (`src/services/config.js`), but mocks can be selected outside production. `src/services/http.js` centralizes authenticated HTTP calls. This audit traces code paths, not server response truth, provider health, tenant isolation, or persistence.

Main endpoint families found in API service modules: auth `/auth/*`; account `/account/*`; admin `/admin/*`; discovery `/discovery/jobs*`; creative/analysis `/creatives*`, `/patterns*`, `/insights*`; media `/media/jobs*`; social/Maps/leadgen `/scout/*`; monitors `/monitors*`; notifications `/notifications*`; dashboard `/dashboard/metrics`; playbooks `/playbooks*`; support `/support/tickets*`; updates `/updates*`. Exact service methods and paths are recorded per route in the evidence JSON. Provider chain and any “real data” claims require runtime/server evidence, which is intentionally not asserted here.

## Comparison and remaining verification

- `5b45806` is available locally. Route changes of note in `src/App.jsx` are `/team/accept` and `/admin/access-requests`; admin navigation gained Access Requests. The current W4 tree also changes auth/session behavior, but this inventory does not re-audit those security flows.
- No shared browser was driven; no managed Preview, backend, database, provider, or credentials were accessed. No screenshot files were created. No route/tab has visual or interaction verification in this subtask.
- Parent should verify EN and AR for each route/tab, especially Discover resolving/results/error, Scout mode and admin queues, Create generation, billing/access copy, admin data-source status and updates publish/preview. Record screenshots under the parent-selected names and mark only directly observed states verified.
