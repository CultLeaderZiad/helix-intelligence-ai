# W4 continuation verification — 2026-10-20

Implementation verified: `696525d244c37a6d3d8906b35a082c2046423347` on `fix/intelligence-W4`, continuing `085ae502367cb1bc788f2d1d3ae868913bbf870a`. Base `fix/intelligence-W3`: `6066dc8b077aebbb8c4e23b0bcf6f556b941e523` (fetched and recorded with `git rev-parse origin/fix/intelligence-W3`). PR: https://github.com/CultLeaderZiad/helix-intelligence-ai/pull/26 (draft; do not merge or deploy).

**This is not a production-readiness claim.** Historical FIXED_VERIFIED rows below are prior-wave records, not fresh proof from this run. Full gates remain blocked as listed here. No production database/data, real account credentials, vendor requests, deployment, or access-control relaxation was used. Native disposable loopback PostgreSQL 16.15 only. Runtime Python 3.12 and Node 24.22.0.

## What changed

| Finding | Result / files |
|---|---|
| W4-01 | Preserved the completed compatibility/forward migrations at 085ae50; reran fresh, drift, dirty-data, rollback and upgrade tests. No migration code rewritten. |
| W4-02 | Fixed real diagnostics in allowed frontend files; eight adjacent W4 test files exercise behavior. CI Node 20 → 24 matches installed Vitest/jsdom engines (Node 20 failed before test workers started). Full unfiltered gates retained. |
| W4-03 | Preserved backend sanitization/logging. ErrorBoundary no longer logs raw thrown values; HTTP validation details normalize to strings. Live error-reporting transport remains unwired/unverified. |
| W4-04 | AuthContext and authService.api guard stale resolution/mutation responses; http retains original account token across retries and ignores stale unauthorized responses. SearchContext caches use user+org scope and purge during session clearing. Impersonation discards administrator credentials and requires fresh admin sign-in to return; server TTL/actor controls retained, not duplicated. |
| W4-05 | No speculative service splits or scraper removal. Existing probe/import repairs retained. Full pyflakes failures are outside the allowlist. |
| W4-06 | LegalPage and EN/AR language layer disclose source-visible processors, R2/local storage, JavaScript-readable session storage, deletion gap, and pending privacy contact. Existing engineering disclosure in docs/compliance/LEGAL_DOCS.md remains unapproved. No erasure implementation claim. |
| W4-07 | LegalPage replaces repeated policies with one explicitly unapproved disclosure requiring Ziad/counsel approval. The separate legacy MarketingFooter remains blocked by scope. |
| W4-08 | Hero, LoopsSection and PricingSection remove sample contacts/scores/brands and trial/pricing promises, describing AI solutions and manual access instead. Existing #product/#pricing navigation anchors preserved. |
| W4-09 | LanguageContext state updater is pure; AuthContext avoids nested state updates; SearchContext persists committed history/drafts in a guarded scope-aware effect, not state updaters. ConfirmDialog refs keep callback/busy updates separate from focus acquire/restore. Storage/chunk handling is guarded in App/ErrorBoundary; page support/onboarding props corrected. |

Changed implementation files: `.github/workflows/ci.yml`, `src/App.jsx`, `src/components/ErrorBoundary.jsx`, `src/components/ui/ConfirmDialog.jsx`, `src/context/AuthContext.jsx`, `src/context/LanguageContext.jsx`, `src/context/SearchContext.jsx`, `src/features/marketing/Hero.jsx`, `src/features/marketing/LoopsSection.jsx`, `src/features/marketing/PricingSection.jsx`, `src/pages/CreatePage.jsx`, `src/pages/DiscoverPage.jsx`, `src/pages/IntelligencePage.jsx`, `src/pages/LegalPage.jsx`, `src/pages/admin/UsersPage.jsx`, `src/services/api/authService.api.js`, `src/services/config.js`, `src/services/http.js`.

New files (all allowed test patterns; no new libraries):
- `src/components/__tests__/ErrorBoundary.w4.test.jsx`: sanitized English/Arabic render failures and blocked storage.
- `src/components/ui/__tests__/ConfirmDialog.w4.test.jsx`: callback changes, busy rerenders, keyboard trapping, StrictMode and opener restoration.
- `src/context/__tests__/auth-context.w4.test.jsx`: terminal session resolution under StrictMode.
- `src/context/__tests__/search-session.w4.test.jsx`: user/org isolation, purge, and committed-once draft persistence.
- `src/features/marketing/__tests__/marketing-w4.test.jsx`: EN/AR honesty, disclosure and navigation anchors.
- `src/services/__tests__/auth-session.w4.test.js`: atomic switch, stale completion and logout races.
- `src/services/__tests__/http-session.w4.test.js`: original-token retries and stale 401 isolation.
- `src/services/__tests__/http-validation.w4.test.js`: structured 422 payload normalization.

## What was verified

| Command | Exit | Observed result |
|---|---:|---|
| `pnpm install --frozen-lockfile` | 0 | Existing lockfile restored; no dependency changes. |
| `pnpm typecheck` | 2 | 483 diagnostics outside changed/allowed implementation and new-test files. Full scope retained; appendix below. |
| `pnpm lint` | 1 | 159 errors outside changed files; zero warnings. Full scope retained; appendix below. |
| `pnpm exec eslint src -f json` | 1 | Same full lint scope, machine-readable inventory below. |
| `pnpm test` | 0 | 5 Node tests and 110 Vitest tests across 14 files passed. |
| `pnpm build` | 0 | Vite production build passed; generated tracked dist/docs metadata restored, not published. |
| `python -m pytest -q tests` (backend) | 1 | 224 passed, 2 failed, 18 warnings. Failures below; no tests skipped/weakened to pass. |
| `python -m pytest -q tests/test_intelligence_w4_*.py` (backend) | 0 | 27 passed; real disposable migration/transaction/concurrency/redaction regressions included. |
| `python -m compileall -q app` (backend) | 0 | Syntax compilation passed. |
| `python -m pyflakes app` (backend) | 1 | 127 diagnostics; all outside permitted backend paths. |
| `python -m alembic upgrade head` (w4_upgrade) | 0 | Fresh upgrade to b7e4c9a1d2f0. |
| `python -m alembic check` (w4_upgrade) | 0 | No new upgrade operations. |
| `python -m alembic upgrade head` (separate w4_rollback) | 0 | Separate disposable rollback database prepared. |
| `python -m alembic downgrade -1` (w4_rollback) | 0 | Downgrade completed. |
| `python -m alembic upgrade head` (w4_rollback) | 0 | Re-upgrade completed. |
| `python -m alembic check` (w4_rollback) | 0 | No drift after rollback/re-upgrade. |
| `git diff --check` | 0 | No whitespace errors. |

Database setup: migrations initially failed because the disposable migration operator lacked CREATEROLE; that operator received CREATEROLE on the isolated cluster and the chain was rerun successfully. The W3 tests require the disposable name helix_test_db; using w4_upgrade initially triggered their safety guard, so full tests were rerun on helix_test_db. Legacy role/event-trigger tests used only the disposable postgres test operator; runtime API used w4_preview with helix_app membership, NOSUPERUSER/NOBYPASSRLS. Runtime/startup/RLS policies were not weakened.

### Full backend test blockers
- `backend/tests/test_intelligence_w2_boundaries.py:106`: asserts raw provider text (`provider down`) is exposed. The current 503 is deliberately sanitized. The test is outside the allowlist; sanitization was not reverted.
- `backend/scripts/prove_prod_schema_reconcile.py:23,394-395`, called from `backend/tests/test_migration_failure.py:27`: legacy helper compares current head to old hard-coded f3d9a7c2b1e4. Its retry upgrade itself succeeded, but head is now b7e4c9a1d2f0. Both helper and test are outside the allowlist.

### Browser checks / evidence
Local managed Vite preview and the actual FastAPI API on the isolated database; no canned API responses or fake results were installed. Test identities were created only in that disposable database. External HTTPS requests were blocked in the browser.
- Landing, manual-access section, and legal draft inspected in EN and AR; document lang/dir changed to ar/rtl. No purchasable prices in the changed access section. Screenshots inspected before sharing.
- Real local admin login, admin user management, member impersonation, and fresh admin sign-in after clearing the impersonated session exercised. No administrator token-return keys remained; logout cleared the token/profile/private cache keys. Initial URL-only transport adjustment was used during local setup; subsequent checks used the existing Vite local API proxy.
- ConfirmDialog: Tab remained inside, Escape dismissed, opener focus restored; Arabic confirmation explains fresh admin sign-in and shows localized cancel/confirm controls. Busy rerender/StrictMode cases are test-proven, not separately browser-proven.
- An early reserved-domain validation request reproduced a render fallback; structured 422 normalization was then fixed and regression-tested. A later deliberate lazy-route abort did not reproduce the final boundary fallback, so final EN/AR boundary screenshots are NOT claimed. ErrorBoundary fallback is unit-tested, not fully browser-proven.
- Existing admin shell/sidebar/public-header/docs copy still has English text in RTL. A pointer hit-test on the RTL sidebar sign-out button was covered by another element; its handler cleared the real session when invoked. This CSS/control issue remains unverified as a normal pointer path; do not treat all browser flows as passing.

Public screenshot evidence (temporary hosted links):
![Local W4 browser checks: landing, admin-granted access, and draft legal disclosures in English and Arabic RTL.](https://dlzlyg5a5kv7c.cloudfront.net/499d45d79c344238baab6f8d8ddcda086893db2c8eb44aa0b0ba520c9ee14368.png)
![Arabic RTL impersonation confirmation, using a disposable local test account; fresh administrator sign-in is required to return.](https://dlzlyg5a5kv7c.cloudfront.net/2e2d6109bc7448979ec9f365ccb36234e45b0788711c42e3a92e42f96e9845f4.png#w=1280&h=577)

## What's unverified

Production/deployment, live providers, real accounts, deletion/erasure end to end, processor/operator contracts, operator-verified privacy contact, legal approval by Ziad/counsel, and live error-reporting transport. DESIGN_SYSTEM.md and intelligence-rereview-5b45806.md were absent. No all-bugs-fixed or readiness assertion is made.

## Blocked

Every diagnostic below requires an existing file outside the explicit allowed list. No ignore rules, typecheck exclusions, blanket casts, rule suppressions, or filtered pyflakes gate were added. Changed implementation files and new tests have no remaining typecheck/lint diagnostics.
- `src/features/marketing/MarketingFooter.jsx`: legacy repeated legal claims and unverified contact; kept unchanged because it is not allowed.
- `src/features/marketing/DocsSection.jsx`: unsupported example API/webhook copy and missing Arabic, outside scope.
- `src/app/PublicHeader.jsx`, `src/app/Sidebar.jsx`: pricing label, incomplete Arabic/chrome and sidebar hit-test behavior require follow-up; outside scope.

## Single P0 next step

**Authorize a bounded follow-up for the listed out-of-allowlist gate/test failures and retained misleading footer/chrome, before any merge or deployment.**

## Diagnostic appendix (exact file and line inventory)

### Typecheck — 483 diagnostics

| File | Diagnostic codes and lines | Reason |
|---|---|---|
| `src/app/AppShell.jsx` | TS2339: 96; TS2741: 57, 160, 163 | Existing file outside allowlist |
| `src/app/CommandBar.jsx` | TS2741: 140, 141 | Existing file outside allowlist |
| `src/app/PublicHeader.jsx` | TS2322: 34 | Existing file outside allowlist |
| `src/app/Sidebar.jsx` | TS2741: 373 | Existing file outside allowlist |
| `src/app/__tests__/OnboardingTour.w3.test.jsx` | TS2322: 18; TS2741: 67 | Existing file outside allowlist |
| `src/app/admin/AdminShell.jsx` | TS2339: 65 | Existing file outside allowlist |
| `src/components/SavedDraftsModal.jsx` | TS2741: 244 | Existing file outside allowlist |
| `src/components/SupportFeedbackModal.jsx` | TS2339: 9, 20, 21, 46, 78 | Existing file outside allowlist |
| `src/components/ui/Button.jsx` | TS2322: 38 | Existing file outside allowlist |
| `src/components/ui/CardSwap.jsx` | TS2339: 15, 341, 344; TS2769: 337 | Existing file outside allowlist |
| `src/components/ui/FloatingSupportButton.jsx` | TS2741: 26 | Existing file outside allowlist |
| `src/components/ui/Metric.jsx` | TS2739: 59 | Existing file outside allowlist |
| `src/components/ui/PillNav.jsx` | TS2322: 52; TS2559: 74, 103 | Existing file outside allowlist |
| `src/components/ui/States.jsx` | TS2741: 131, 152, 160 | Existing file outside allowlist |
| `src/components/ui/__tests__/PillNav.w3.test.jsx` | TS2739: 12 | Existing file outside allowlist |
| `src/features/admin/OrganizationsTable.jsx` | TS2741: 62, 71 | Existing file outside allowlist |
| `src/features/admin/OverviewStatStrip.jsx` | TS2741: 50, 56, 65, 72, 78, 84 | Existing file outside allowlist |
| `src/features/admin/RecentJobsTable.jsx` | TS2741: 67 | Existing file outside allowlist |
| `src/features/admin/UsersTable.jsx` | TS2741: 59, 65, 70 | Existing file outside allowlist |
| `src/features/auth/PasswordStrength.jsx` | TS2741: 25 | Existing file outside allowlist |
| `src/features/discover/CreativeDetailPanel.jsx` | TS2739: 248, 302, 303, 304, 341, 354, 358, 367; TS2741: 233, 268, 334 | Existing file outside allowlist |
| `src/features/discover/FilterRail.jsx` | TS2739: 81, 95; TS2741: 66, 67, 76, 92, 106, 134, 135, 144, 145 | Existing file outside allowlist |
| `src/features/discover/JobProgress.jsx` | TS2741: 110 | Existing file outside allowlist |
| `src/features/discover/ResultsTable.jsx` | TS2741: 120, 132 | Existing file outside allowlist |
| `src/features/discover/SearchQueryBar.jsx` | TS2741: 73, 89, 134 | Existing file outside allowlist |
| `src/features/docs/DocsLayout.jsx` | TS2322: 242; TS2741: 150, 503 | Existing file outside allowlist |
| `src/features/docs/MarkdownRenderer.jsx` | TS2741: 332 | Existing file outside allowlist |
| `src/features/docs/docsData.js` | TS2339: 11 | Existing file outside allowlist |
| `src/features/marketing/DocsSection.jsx` | TS2322: 44, 48 | Existing file outside allowlist |
| `src/features/scout-leadgen/LeadsTable.jsx` | TS2741: 92 | Existing file outside allowlist |
| `src/hooks/__tests__/adapter-cancellation.w3.test.jsx` | TS2339: 62, 103, 152, 164, 192, 193; TS2532: 117 | Existing file outside allowlist |
| `src/hooks/__tests__/request-lifecycle.w3.test.jsx` | TS2349: 54, 55, 75, 95, 110, 128; TS2538: 50, 51, 57, 62, 75, 76, 91, 99, 105, 108, 113, 118, 123, 128, 129, 133, 139, 149, 150, 152, 166, 167, 169; TS2722: 54, 55, 65, 82, 84, 95, 110, 160, 174, 188, 201, 217, 218 | Existing file outside allowlist |
| `src/hooks/useAdminOverview.js` | TS2339: 45 | Existing file outside allowlist |
| `src/hooks/useDiscoverySearch.js` | TS2339: 32, 78; TS2353: 37, 75, 110 | Existing file outside allowlist |
| `src/hooks/useLeadGenJob.js` | TS1003: 5 | Existing file outside allowlist |
| `src/lib/analytics.js` | TS2339: 25, 28, 44, 45, 50, 51 | Existing file outside allowlist |
| `src/lib/utm.js` | TS2322: 119 | Existing file outside allowlist |
| `src/pages/ApiKeysPage.jsx` | TS2322: 489, 495; TS2739: 250 | Existing file outside allowlist |
| `src/pages/BillingPage.jsx` | TS2739: 107; TS2741: 350 | Existing file outside allowlist |
| `src/pages/DashboardPage.jsx` | TS2739: 149, 160; TS2741: 151, 203 | Existing file outside allowlist |
| `src/pages/GuidePage.jsx` | TS2741: 194, 198, 225, 228, 231, 333, 338, 343, 348, 353, 358 | Existing file outside allowlist |
| `src/pages/LandingPage.jsx` | TS2741: 25, 37 | Existing file outside allowlist |
| `src/pages/MonitorsPage.jsx` | TS2739: 411, 457; TS2741: 89, 90, 91, 152, 173, 174, 179, 189, 198, 233, 325, 339, 385, 386, 387, 392, 413, 416, 417, 418, 421, 427, 451, 452, 453 | Existing file outside allowlist |
| `src/pages/NotFoundPage.jsx` | TS2322: 18; TS2739: 12; TS2741: 13 | Existing file outside allowlist |
| `src/pages/NotificationsPage.jsx` | TS2741: 116 | Existing file outside allowlist |
| `src/pages/PendingLoopPage.jsx` | TS2322: 26; TS2739: 20; TS2741: 21 | Existing file outside allowlist |
| `src/pages/PerformancePage.jsx` | TS2741: 86, 89, 90, 91, 94, 261, 279, 303, 307, 312, 569 | Existing file outside allowlist |
| `src/pages/ProfileSettingsPage.jsx` | TS2739: 114 | Existing file outside allowlist |
| `src/pages/PublicPlaybookPage.jsx` | TS2741: 164 | Existing file outside allowlist |
| `src/pages/ScoutLeadGenerationPage.jsx` | TS1003: 19 | Existing file outside allowlist |
| `src/pages/ScoutPage.jsx` | TS2741: 412 | Existing file outside allowlist |
| `src/pages/SupportPage.jsx` | TS2739: 83 | Existing file outside allowlist |
| `src/pages/SwipeFilesPage.jsx` | TS2739: 204; TS2741: 385, 393 | Existing file outside allowlist |
| `src/pages/TeamPage.jsx` | TS2322: 193; TS2739: 135 | Existing file outside allowlist |
| `src/pages/__tests__/team-accept-w1.test.mjs` | TS2307: 1, 2, 3 | Existing file outside allowlist |
| `src/pages/admin/AdminPendingPage.jsx` | TS2322: 25; TS2739: 19; TS2741: 20 | Existing file outside allowlist |
| `src/pages/admin/AuditLogPage.jsx` | TS2739: 174; TS2741: 72, 76, 154, 162, 163, 164, 240, 249, 305 | Existing file outside allowlist |
| `src/pages/admin/DataSourcesPage.jsx` | TS2739: 297; TS2741: 165, 169, 246, 285, 286, 287, 317 | Existing file outside allowlist |
| `src/pages/admin/OrganizationsPage.jsx` | TS2322: 189, 195; TS2345: 70, 289 | Existing file outside allowlist |
| `src/pages/admin/OverviewPage.jsx` | TS2739: 39; TS2741: 28, 32, 51, 52, 54, 65, 66, 68, 82, 83, 85, 96, 97, 99 | Existing file outside allowlist |
| `src/pages/admin/ScrapeJobsPage.jsx` | TS2739: 196; TS2741: 92, 107, 184, 185, 186, 240, 291, 308 | Existing file outside allowlist |
| `src/pages/admin/SubscriptionsPlansPage.jsx` | TS2345: 82, 83, 118, 119, 120, 121, 328, 337, 349, 358, 435, 445 | Existing file outside allowlist |
| `src/pages/admin/SystemHealthPage.jsx` | TS2739: 141; TS2741: 51, 55, 76, 129, 130, 131, 161 | Existing file outside allowlist |
| `src/pages/admin/UpdatesPage.jsx` | TS2741: 543, 604, 686 | Existing file outside allowlist |
| `src/pages/auth/ForgotPasswordPage.jsx` | TS2739: 84, 169; TS2741: 71, 149, 154 | Existing file outside allowlist |
| `src/pages/auth/ResetPasswordPage.jsx` | TS2739: 97, 102, 127; TS2741: 125 | Existing file outside allowlist |
| `src/pages/auth/SignInPage.jsx` | TS2339: 129, 139, 141, 148, 165, 167; TS2739: 129; TS2741: 109, 114, 145 | Existing file outside allowlist |
| `src/pages/auth/SignUpPage.jsx` | TS2339: 193, 203, 205, 209, 218, 220, 224, 232, 234, 248, 265, 266; TS2739: 193, 209, 224; TS2741: 164, 169, 178, 238 | Existing file outside allowlist |
| `src/pages/docs/DocsHomePage.jsx` | TS2741: 73, 384 | Existing file outside allowlist |
| `src/pages/docs/ScoutCliDocsPage.jsx` | TS2322: 71 | Existing file outside allowlist |
| `src/services/__tests__/http.w3.test.js` | TS18048: 51; TS2339: 9, 23, 34, 44, 56, 73, 82, 91 | Existing file outside allowlist |
| `src/services/__tests__/mock-cancellation.w3.test.js` | TS2349: 23 | Existing file outside allowlist |
| `src/services/__tests__/sessionStore.w0.test.js` | TS2307: 1, 2; TS2322: 19; TS2739: 20, 21 | Existing file outside allowlist |
| `src/services/api/discoverService.api.js` | TS2339: 17, 27, 31 | Existing file outside allowlist |
| `src/services/api/leadgen.js` | TS1003: 8 | Existing file outside allowlist |
| `src/services/api/mediaService.api.js` | TS2339: 4, 16, 28, 32, 49 | Existing file outside allowlist |
| `src/services/api/monitorService.api.js` | TS2339: 34 | Existing file outside allowlist |
| `src/services/mock/accountService.mock.js` | TS2339: 85, 91 | Existing file outside allowlist |
| `src/services/mock/adminService.mock.js` | TS2322: 213; TS2362: 193; TS2363: 193 | Existing file outside allowlist |
| `src/services/mock/authService.mock.js` | TS2694: 104, 113, 114, 135, 136; TS2741: 187 | Existing file outside allowlist |
| `src/services/mock/creativeService.mock.js` | TS2322: 50 | Existing file outside allowlist |
| `src/services/mock/discoverService.mock.js` | TS2322: 215, 232; TS2339: 178, 223, 241; TS2362: 86, 296; TS2363: 86, 296 | Existing file outside allowlist |
| `src/services/mock/latency.js` | TS2339: 9 | Existing file outside allowlist |
| `src/services/mock/mediaService.mock.js` | TS2339: 7, 68, 75, 85; TS2559: 71, 78, 80 | Existing file outside allowlist |
| `src/services/mock/simulationService.mock.js` | TS2741: 88 | Existing file outside allowlist |

### ESLint — 159 errors

| File | Lines and messages | Reason |
|---|---|---|
| `src/app/ProtectedRoute.jsx` | 1: 'useEffect' is defined but never used. | Existing file outside allowlist |
| `src/app/Sidebar.jsx` | 3: 'UserCheck' is defined but never used.; 8: 'KeyHint' is defined but never used. | Existing file outside allowlist |
| `src/app/navigation.js` | 1: 'BookOpen' is defined but never used. | Existing file outside allowlist |
| `src/components/LanguageSwitcher.jsx` | 3: 'Globe' is defined but never used. | Existing file outside allowlist |
| `src/components/NotificationBell.jsx` | 37: 'loading' is assigned a value but never used.; 37: 'setLoading' is assigned a value but never used. | Existing file outside allowlist |
| `src/components/OnboardingWizardModal.jsx` | 3: 'accountService' is defined but never used.; 47: 'competitorText' is assigned a value but never used.; 47: 'setCompetitorText' is assigned a value but never used.; 49: 'setIsSubmitting' is assigned a value but never used. | Existing file outside allowlist |
| `src/components/SavedDraftsModal.jsx` | 2: 'Search' is defined but never used.; 2: 'Sparkles' is defined but never used.; 4: 'Panel' is defined but never used. | Existing file outside allowlist |
| `src/features/discover/CreativeDetailPanel.jsx` | 227: 'url' is assigned a value but never used. | Existing file outside allowlist |
| `src/features/discover/EntityDossierCard.jsx` | 4: 'ShieldAlert' is defined but never used.; 5: 'Tv' is defined but never used.; 11: 'Share2' is defined but never used.; 13: 'Target' is defined but never used.; 15: 'Users' is defined but never used.; 17: 'Video' is defined but never used.; 186: 'isRtl' is assigned a value but never used. | Existing file outside allowlist |
| `src/features/discover/FilterRail.jsx` | 2: 'Button' is defined but never used. | Existing file outside allowlist |
| `src/features/docs/DocSearchModal.jsx` | 7: 'ChevronRight' is defined but never used.; 10: 'FileText' is defined but never used.; 12: 'ArrowUpDown' is defined but never used.; 13: 'Sparkles' is defined but never used.; 15: 'DOCS_REGISTRY' is defined but never used. | Existing file outside allowlist |
| `src/features/docs/DocsLayout.jsx` | 13: 'Sparkles' is defined but never used.; 14: 'Layers' is defined but never used.; 18: 'CheckCircle2' is defined but never used.; 19: 'FileText' is defined but never used.; 22: 'searchDocs' is defined but never used.; 31: 'navigate' is assigned a value but never used. | Existing file outside allowlist |
| `src/features/scout/MapsLeadDetailPanel.jsx` | 2: 'Building2' is defined but never used. | Existing file outside allowlist |
| `src/features/scout/MapsLeadsTable.jsx` | 2: 'Share2' is defined but never used.; 2: 'Copy' is defined but never used. | Existing file outside allowlist |
| `src/features/scout/MapsQueryForm.jsx` | 2: 'Sparkles' is defined but never used. | Existing file outside allowlist |
| `src/features/scout/ScoutJobProgress.jsx` | 42: 'isVerified' is assigned a value but never used.; 43: 'isOk' is assigned a value but never used. | Existing file outside allowlist |
| `src/features/scout/ScoutModeTabs.jsx` | 2: 'CheckCircle2' is defined but never used.; 2: 'ShieldCheck' is defined but never used. | Existing file outside allowlist |
| `src/features/scout/TargetCategoryField.jsx` | 2: 'Sparkles' is defined but never used. | Existing file outside allowlist |
| `src/hooks/useAsync.js` | 43: Definition for rule 'react-hooks/exhaustive-deps' was not found.; 52: Definition for rule 'react-hooks/exhaustive-deps' was not found. | Existing file outside allowlist |
| `src/pages/ApiKeysPage.jsx` | 18: 'Check' is defined but never used.; 21: 'ArrowRight' is defined but never used. | Existing file outside allowlist |
| `src/pages/BillingPage.jsx` | 8: 'CheckCircle2' is defined but never used.; 9: 'AlertTriangle' is defined but never used.; 34: 'error' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/DashboardPage.jsx` | 16: 'ExternalLink' is defined but never used. | Existing file outside allowlist |
| `src/pages/GuidePage.jsx` | 11: 'Bookmark' is defined but never used.; 13: 'CreditCard' is defined but never used.; 14: 'Sparkles' is defined but never used.; 15: 'Zap' is defined but never used.; 16: 'ArrowRight' is defined but never used.; 18: 'Flame' is defined but never used.; 19: 'Clock' is defined but never used.; 21: 'HelpCircle' is defined but never used.; 22: 'Code' is defined but never used.; 23: 'Sliders' is defined but never used.; 24: 'Database' is defined but never used.; 25: 'Cpu' is defined but never used. | Existing file outside allowlist |
| `src/pages/MonitorsPage.jsx` | 26: 'react' import is duplicated. | Existing file outside allowlist |
| `src/pages/NotificationsPage.jsx` | 3: 'Sparkles' is defined but never used.; 3: 'Trash2' is defined but never used. | Existing file outside allowlist |
| `src/pages/PerformancePage.jsx` | 14: 'Flame' is defined but never used.; 20: 'CheckCircle' is defined but never used.; 23: 'ArrowUpRight' is defined but never used. | Existing file outside allowlist |
| `src/pages/ProfileSettingsPage.jsx` | 2: 'Mail' is defined but never used.; 8: 'user' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/PublicPlaybookPage.jsx` | 3: 'ExternalLink' is defined but never used. | Existing file outside allowlist |
| `src/pages/PublicUpdatesPage.jsx` | 12: 'SlidersHorizontal' is defined but never used.; 13: 'ChevronRight' is defined but never used. | Existing file outside allowlist |
| `src/pages/ScoutLeadGenerationPage.jsx` | 70: 'offline' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/ScoutPage.jsx` | 3: 'RefreshCw' is defined but never used.; 3: 'ArrowRight' is defined but never used. | Existing file outside allowlist |
| `src/pages/SupportPage.jsx` | 2: 'ChevronRight' is defined but never used.; 9: 'user' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/SwipeFilesPage.jsx` | 12: 'ExternalLink' is defined but never used.; 15: 'FolderPlus' is defined but never used.; 17: 'Tag' is defined but never used.; 24: 'Play' is defined but never used.; 25: 'ArrowRight' is defined but never used.; 34: 'isRtl' is assigned a value but never used.; 38: 'error' is assigned a value but never used.; 39: 'setActiveCollection' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/TeamPage.jsx` | 9: 'Mail' is defined but never used.; 13: 'ShieldCheck' is defined but never used.; 14: 'Copy' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/AuditLogPage.jsx` | 11: 'Search' is defined but never used.; 16: 'Shield' is defined but never used.; 17: 'Activity' is defined but never used.; 18: 'User' is defined but never used.; 19: 'Clock' is defined but never used.; 20: 'Coins' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/DataSourcesPage.jsx` | 11: 'Activity' is defined but never used.; 13: 'CheckCircle2' is defined but never used.; 14: 'AlertTriangle' is defined but never used.; 15: 'XCircle' is defined but never used.; 16: 'Server' is defined but never used.; 17: 'Cpu' is defined but never used.; 18: 'Radio' is defined but never used.; 19: 'ShieldCheck' is defined but never used.; 20: 'Zap' is defined but never used.; 22: 'ExternalLink' is defined but never used.; 23: 'Layers' is defined but never used.; 106: 'activeTab' is assigned a value but never used.; 106: 'setActiveTab' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/admin/FeatureFlagsPage.jsx` | 3: 'Sliders' is defined but never used.; 3: 'CheckCircle2' is defined but never used.; 3: 'ShieldCheck' is defined but never used.; 7: 'orgs' is assigned a value but never used.; 9: 'error' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/admin/OrganizationsPage.jsx` | 9: 'AlertTriangle' is defined but never used.; 12: 'PlusCircle' is defined but never used.; 13: 'ShieldAlert' is defined but never used.; 21: 'error' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/admin/ScrapeJobsPage.jsx` | 13: 'CheckCircle2' is defined but never used.; 14: 'XCircle' is defined but never used.; 15: 'Clock' is defined but never used.; 16: 'Play' is defined but never used.; 17: 'ExternalLink' is defined but never used.; 18: 'Layers' is defined but never used.; 19: 'Database' is defined but never used.; 20: 'ArrowUpDown' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/SubscriptionsPlansPage.jsx` | 8: 'Sparkles' is defined but never used.; 11: 'ShieldCheck' is defined but never used.; 20: 'error' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/admin/SupportAdminPage.jsx` | 2: 'CheckCircle2' is defined but never used.; 2: 'Clock' is defined but never used.; 2: 'Filter' is defined but never used.; 2: 'ChevronRight' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/SystemHealthPage.jsx` | 12: 'CheckCircle2' is defined but never used.; 13: 'AlertTriangle' is defined but never used.; 14: 'Server' is defined but never used.; 18: 'Radio' is defined but never used.; 19: 'Clock' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/UpdatesPage.jsx` | 19: 'Calendar' is defined but never used.; 20: 'Bold' is defined but never used.; 21: 'List' is defined but never used.; 22: 'Heading' is defined but never used.; 23: 'LinkIcon' is defined but never used. | Existing file outside allowlist |
| `src/pages/admin/UsagePage.jsx` | 14: 'User' is defined but never used.; 15: 'Building' is defined but never used.; 21: 'error' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/auth/ForgotPasswordPage.jsx` | 29: 'isSlow' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/auth/ResetPasswordPage.jsx` | 10: 'Input' is defined but never used. | Existing file outside allowlist |
| `src/pages/auth/SignInPage.jsx` | 22: 'isResolving' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/auth/SignUpPage.jsx` | 13: 'ServiceError' is defined but never used. | Existing file outside allowlist |
| `src/pages/docs/DocsHomePage.jsx` | 11: 'Terminal' is defined but never used.; 12: 'Zap' is defined but never used.; 13: 'HelpCircle' is defined but never used.; 14: 'ExternalLink' is defined but never used.; 19: 'DOCS_REGISTRY' is defined but never used.; 54: 'navigate' is assigned a value but never used. | Existing file outside allowlist |
| `src/pages/docs/ScoutCliDocsPage.jsx` | 3: 'Download' is defined but never used.; 3: 'Shield' is defined but never used. | Existing file outside allowlist |
| `src/services/mock/adminService.mock.js` | 1: 'ServiceError' is defined but never used. | Existing file outside allowlist |

### Full pyflakes — 127 diagnostics

| File:line | Diagnostic | Reason |
|---|---|---|
| `backend/app/api/routers/notifications.py:1` | 'fastapi.Path' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/notifications.py:3` | 'typing.Dict' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/notifications.py:3` | 'typing.Any' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/support.py:1` | 'fastapi.HTTPException' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/support.py:1` | 'fastapi.Query' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/support.py:3` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/updates.py:5` | 'sqlalchemy.and_' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/updates.py:7` | 'app.core.deps.get_current_user' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:1` | 'os' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:2` | 'uuid' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:4` | 'fastapi.Body' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:4` | 'fastapi.Form' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:6` | 'sqlalchemy.desc' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:7` | 'typing.Dict' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:7` | 'typing.Any' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/account.py:219` | 'app.services.billing_service._ensure_daily_reset' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/creatives.py:1` | 'fastapi.Query' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/discover.py:1` | 'fastapi.Query' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/playbooks.py:1` | 'fastapi.HTTPException' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/providers.py:11` | 'app.models.organization.Organization' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/providers.py:14` | 'app.services.security_service.mask_api_key' imported but unused | Existing file outside allowlist |
| `backend/app/api/routers/providers.py:94` | local variable 'test_res' is assigned to but never used | Existing file outside allowlist |
| `backend/app/models/__init__.py:1` | 'app.db.base.Base' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:2` | '.user.User' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:3` | '.organization.Organization' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:4` | '.scrape_job.ScrapeJob' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:5` | '.creative.Creative' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:6` | '.creative_score.CreativeScore' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:7` | '.pattern.Pattern' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:8` | '.ai_insight.AIInsight' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:9` | '.usage_log.UsageLog' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:10` | '.plan.Plan' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:11` | '.saved_creative.SavedCreative' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:12` | '.api_key.ApiKey' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:13` | '.notification.Notification' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:14` | '.organization_member.OrganizationMember' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:14` | '.organization_member.OrganizationInvite' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:15` | '.api_usage.ExternalApiUsage' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:16` | '.media_job.MediaGenerationJob' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:17` | '.webhook_event.WebhookEvent' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:18` | '.app_update.AppUpdate' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:19` | '.workspace_credential.WorkspaceProviderCredential' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:20` | '.support_ticket.SupportTicket' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:20` | '.support_ticket.SupportTicketReply' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:21` | '.playbook.Playbook' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:22` | '.simulation_report.SimulationReport' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:23` | '.monitor.Monitor' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:23` | '.monitor.MonitorRun' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:23` | '.monitor.MonitorCreative' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:23` | '.monitor.MonitorEvent' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:24` | '.scout.ScoutJob' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:24` | '.scout.ScoutLead' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:24` | '.scout.ScoutMapsJob' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:24` | '.scout.ScoutMapsLead' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:25` | '.leadgen.LeadGenJob' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:25` | '.leadgen.LeadGenLead' imported but unused | Existing file outside allowlist |
| `backend/app/models/__init__.py:25` | '.leadgen.LeadGenWorkerHeartbeat' imported but unused | Existing file outside allowlist |
| `backend/app/models/organization.py:1` | 'sqlalchemy.func' imported but unused | Existing file outside allowlist |
| `backend/app/models/organization.py:2` | 'sqlalchemy.orm.relationship' imported but unused | Existing file outside allowlist |
| `backend/app/models/creative.py:3` | 'sqlalchemy.Index' imported but unused | Existing file outside allowlist |
| `backend/app/models/creative.py:4` | 'sqlalchemy.orm.relationship' imported but unused | Existing file outside allowlist |
| `backend/app/models/scrape_job.py:5` | 'sqlalchemy.orm.relationship' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:1` | '.common.Paginated' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:1` | '.common.ServiceErrorShape' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:2` | '.auth.UserCreate' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:2` | '.auth.UserLogin' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:2` | '.auth.SessionResponse' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:3` | '.discover.SearchParams' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:3` | '.discover.Job' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:4` | '.creative.Creative' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:4` | '.creative.Scores' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:4` | '.creative.CreativeMetrics' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:4` | '.creative.Brand' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:5` | '.analysis.Pattern' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:5` | '.analysis.Insight' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:6` | '.admin.AdminOverviewStats' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:6` | '.admin.AdminJobRow' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:6` | '.admin.AdminSystemHealth' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/__init__.py:6` | '.admin.AdminServiceHealth' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/common.py:1` | 'pydantic.ConfigDict' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/common.py:2` | 'typing.Any' imported but unused | Existing file outside allowlist |
| `backend/app/schemas/discover.py:2` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:1` | '.auth_service.authenticate_user' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:1` | '.auth_service.register_user' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:2` | '.discover_service.trigger_search' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:2` | '.discover_service.get_job_status' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:3` | '.creative_service.list_creatives' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:4` | '.analysis_service.get_creative_insight' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:5` | '.admin_service.get_overview' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:5` | '.admin_service.list_jobs' imported but unused | Existing file outside allowlist |
| `backend/app/services/__init__.py:5` | '.admin_service.get_health' imported but unused | Existing file outside allowlist |
| `backend/app/services/atlas_pipeline.py:224` | local variable 'is_verified' is assigned to but never used | Existing file outside allowlist |
| `backend/app/services/lifecycle_email_service.py:18` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/services/notification_service.py:1` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/services/notification_service.py:5` | 'app.models.user.User' imported but unused | Existing file outside allowlist |
| `backend/app/services/notification_service.py:44` | local variable 'unread_count' is assigned to but never used | Existing file outside allowlist |
| `backend/app/services/support_service.py:1` | 'datetime' imported but unused | Existing file outside allowlist |
| `backend/app/services/support_service.py:4` | 'sqlalchemy.update' imported but unused | Existing file outside allowlist |
| `backend/app/services/support_service.py:5` | 'fastapi.status' imported but unused | Existing file outside allowlist |
| `backend/app/services/admin_service.py:5` | 'sqlalchemy.desc' imported but unused | Existing file outside allowlist |
| `backend/app/services/admin_service.py:5` | 'sqlalchemy.update' imported but unused | Existing file outside allowlist |
| `backend/app/services/api_key_service.py:4` | 'typing.Optional' imported but unused | Existing file outside allowlist |
| `backend/app/services/api_key_service.py:6` | 'sqlalchemy.delete' imported but unused | Existing file outside allowlist |
| `backend/app/services/auth_service.py:5` | 'app.schemas.auth.SessionResponse' imported but unused | Existing file outside allowlist |
| `backend/app/services/dashboard_service.py:11` | 'app.models.organization.Organization' imported but unused | Existing file outside allowlist |
| `backend/app/services/entity_intelligence.py:13` | 're' imported but unused | Existing file outside allowlist |
| `backend/app/services/maps_scout_service.py:18` | 'app.services.scrapegraph_lead_service.extract_profile_with_scrapegraph' imported but unused | Existing file outside allowlist |
| `backend/app/services/maps_scout_service.py:313` | import 'safe_request_async' from line 258 shadowed by loop variable | Existing file outside allowlist |
| `backend/app/services/maps_scout_service.py:415` | f-string is missing placeholders | Existing file outside allowlist |
| `backend/app/services/playbook_service.py:9` | 'app.models.organization.Organization' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:7` | 're' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:8` | 'asyncio' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:12` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:12` | 'typing.Tuple' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:13` | 'sqlalchemy.ext.asyncio.AsyncSession' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:14` | 'sqlalchemy.update' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:31` | 'app.services.scout_parse.parse_line' imported but unused | Existing file outside allowlist |
| `backend/app/services/scout_service.py:373` | local variable 'atlas_err' is assigned to but never used | Existing file outside allowlist |
| `backend/app/services/scrapegraph_lead_service.py:5` | 'typing.Union' imported but unused | Existing file outside allowlist |
| `backend/app/services/team_service.py:3` | 'typing.List' imported but unused | Existing file outside allowlist |
| `backend/app/services/team_service.py:5` | 'sqlalchemy.delete' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/ad_library_provider.py:3` | 'asyncio' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/adyntel_provider.py:1` | 'os' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/adyntel_provider.py:2` | 'asyncio' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/metapi_provider.py:1` | 'os' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/scrapegraph_provider.py:1` | 'os' imported but unused | Existing file outside allowlist |
| `backend/app/services/scraping/scrapegraph_provider.py:2` | 'asyncio' imported but unused | Existing file outside allowlist |

---

# Helix Intelligence — Production-Readiness Remediation Ledger (F01–F82)

**Audited Revision**: 0a8164920031a8dfaa036e2a67ee6f107a48a9f2  
**Working Branch**: main  
**Total Findings**: 82 (82 FIXED_VERIFIED, 0 OPEN)  

| ID | Severity | Area | Title | Status | Changed Files | Regression Test | External Follow-up |
|---|---|---|---|---|---|---|---|
| F01 | P0 | Schema | The incident class remains: models and migrations describe different databases. | FIXED_VERIFIED | backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py, backend/alembic/env.py, backend/app/models/creative.py, backend/app/models/scout.py | alembic upgrade head && alembic check against fresh Neon PostgreSQL test branch. | None |
| F02 | P0 | Authentication | A shared external-auth marker is a working password. | FIXED_VERIFIED | backend/app/core/security.py, backend/tests/test_auth_reset_suite.py | test_auth_reset_suite.py::test_f02_external_auth_managed_cannot_login_with_password | None |
| F03 | P0 | Tenant isolation | Saving a foreign creative bypasses the scoped creative GET. | FIXED_VERIFIED | backend/app/services/creative_service.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f03_creative_save_cross_tenant_isolation | None |
| F04 | P0 | Tenant isolation | Playbook compilation publishes other tenants’ data. | FIXED_VERIFIED | backend/app/services/playbook_service.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f04_playbook_compile_cross_tenant_isolation | None |
| F05 | P0 | Tenant isolation | Brand and pattern lists are global. | FIXED_VERIFIED | backend/app/services/creative_service.py, backend/app/api/routers/creatives.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f05_brands_and_patterns_tenant_scoping | None |
| F06 | P0 | Tenant isolation | Insight/simulation creation accepts foreign creative IDs. | FIXED_VERIFIED | backend/app/services/analysis_service.py, backend/app/services/simulation_service.py, backend/app/api/routers/creatives.py, backend/app/api/routers/simulation.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f06_insights_and_simulation_cross_tenant_isolation | None |
| F07 | P0 | Credits | Concurrent charges lose deductions despite FOR UPDATE. | FIXED_VERIFIED | backend/app/services/billing_service.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f07_f10_atomic_charge_and_idempotency_key | None |
| F08 | P0 | Credits | Refunds can mint credits or be lost permanently. | FIXED_VERIFIED | backend/app/services/billing_service.py, backend/app/services/job_reconciliation.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f08_idempotent_refund_and_reconciliation_sweeper | None |
| F09 | P0 | Credits / truthfulness | Provider outages produce charged fabricated analysis. | FIXED_VERIFIED | backend/app/services/ai/base.py, backend/app/services/analysis_service.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f09_provider_outage_raises_honest_503_without_charging | None |
| F10 | P0 | Credits / retries | Transport retries replay paid mutations. | FIXED_VERIFIED | src/services/http.js, backend/app/services/billing_service.py, backend/app/api/routers/scout.py, backend/app/api/routers/leadgen.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f10_http_js_restricts_mutation_retries | None |
| F11 | P0 | Media quotas | Concurrent media jobs bypass generation quotas. | FIXED_VERIFIED | backend/app/services/billing_service.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f11_f55_inflight_concurrency_and_per_plan_quotas | None |
| F12 | P0 | Privacy | Workspace data survives account changes in the same browser. | FIXED_VERIFIED | src/context/SearchContext.jsx, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f12_f43_search_history_storage_isolation | None |
| F13 | P1 | Migrations | A fresh alembic upgrade fails. | FIXED_VERIFIED | backend/alembic/versions/46af201944fd_add_is_suspended_to_users.py, backend/alembic/versions/a1b2c3d4e5f6_add_leadgen_tables.py | alembic upgrade head from empty database. | None |
| F14 | P1 | Startup / schema | Startup changes schema outside Alembic and continues after schema errors. | FIXED_VERIFIED | backend/app/main.py, render.yaml | Inspection of main.py lifespan and render.yaml. | None |
| F15 | P1 | Readiness | Health reports success during DB/schema outages. | FIXED_VERIFIED | backend/app/api/routers/health.py | Unit tests and router inspection for /api/health/live and /api/health/ready. | None |
| F16 | P1 | CI | The existing gates cannot catch the reported incident or runtime name errors. | FIXED_VERIFIED | .github/workflows/ci.yml | GitHub Actions workflow YAML validation and local test/pyflakes runs. | None |
| F17 | P1 | Password reset | Forgot-password sends no email and logs the usable reset token. | FIXED_VERIFIED | backend/app/api/routers/auth.py, backend/app/services/email_service.py | test_auth_reset_suite.py::test_f17_forgot_password_does_not_log_plain_token | None |
| F18 | P1 | Password reset | Reset tokens are not atomically single-use; stale links invalidate new links. | FIXED_VERIFIED | backend/app/services/auth_service.py, backend/tests/test_auth_reset_suite.py | test_auth_reset_suite.py::test_f18_stale_reset_link_does_not_destroy_new_link | None |
| F19 | P1 | Session lifecycle | Logout and password resets do not revoke stolen sessions. | FIXED_VERIFIED | backend/app/core/security.py, backend/app/core/deps.py, backend/app/services/auth_service.py, backend/app/api/routers/account.py, backend/app/api/routers/auth.py, backend/tests/test_auth_reset_suite.py | test_auth_reset_suite.py::test_f19_token_revocation_on_reset | None |
| F20 | P1 | Secrets | Meta access-token literals are committed. | FIXED_VERIFIED | backend/scripts/inspect_meta_token.py, backend/scripts/test_new_meta.py | Static analysis on scripts folder and git grep. | None |
| F21 | P1 | Secrets | Scout credentials are stored as plaintext JSON. | FIXED_VERIFIED | backend/app/api/routers/scout.py, backend/app/services/scout_service.py, backend/app/services/leadgen_pipeline.py, backend/app/services/security_service.py, backend/tests/test_byok_suite.py | test_byok_suite.py::test_f21_scout_credentials_encrypted_in_db | None |
| F22 | P1 | Secrets in URLs | BYOK credentials and the JWT signing secret are accepted in query strings. | FIXED_VERIFIED | backend/app/api/routers/creatives.py, src/services/api/analysisService.api.js, backend/tests/test_byok_suite.py | test_byok_suite.py::test_f22_byok_query_params_rejected | None |
| F23 | P1 | SSRF | URL guards allow private network fetches. | FIXED_VERIFIED | backend/app/services/security_service.py, backend/app/services/leadgen_pipeline.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f23_ssrf_ipv4_mapped_ipv6_and_private_host_blocking, test_f23_safe_http_get_hop_by_hop_redirect_safety | None |
| F24 | P1 | Worker | The worker reuses async database connections across destroyed event loops. | FIXED_VERIFIED | backend/app/db/session.py, backend/workers/scrapling/worker.py, backend/app/services/leadgen_pipeline.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f24_worker_engine_uses_nullpool | None |
| F25 | P1 | Job durability | Background tasks are not a durable queue; Scout/Maps/leadgen lack dead-job recovery. | FIXED_VERIFIED | backend/app/api/routers/scout.py, backend/app/services/media_service.py, backend/app/services/job_reconciliation.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f25_reconciliation_sweeper_handles_all_job_types | None |
| F26 | P1 | Worker availability | An enabled flag is treated as a live worker. | FIXED_VERIFIED | backend/app/api/routers/leadgen.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f26_live_worker_health_verification | None |
| F27 | P1 | Leadgen billing | Leadgen bypasses billing policy and overwrites the user’s spend ceiling. | FIXED_VERIFIED | backend/app/api/routers/leadgen.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f27_leadgen_budget_ceiling_rejection_and_charge | None |
| F28 | P1 | Credits / providers | Failed Scout/Maps/leadgen jobs retain their upfront charges. | FIXED_VERIFIED | backend/app/services/scout_service.py, backend/app/services/maps_scout_service.py, backend/app/services/leadgen_pipeline.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f28_prework_failure_refunds_deducted_credits | None |
| F29 | P1 | Discovery truthfulness | Provider failure is reported as a successful empty search and charged. | FIXED_VERIFIED | backend/app/services/scraping/ad_library_provider.py, backend/app/services/discover_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_discovery_provider_outage_and_refund | None |
| F30 | P1 | Leadgen pause/resume | Pause uses a stale object and resume never selects the checkpoint path. | FIXED_VERIFIED | backend/app/services/leadgen_pipeline.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_leadgen_checkpoint_resume_and_pause_refresh | None |
| F31 | P1 | AI runtime | Default AI provider construction raises NameError. | FIXED_VERIFIED | backend/app/services/ai/ai_router.py | Import inspection and static verification in ai_router.py. | None |
| F32 | P1 | Paid plans | Upgraded users remain subject to expired-trial AI gates. | FIXED_VERIFIED | backend/app/services/ai/ai_router.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f32_paid_user_bypasses_trial_expiration_and_limits | None |
| F33 | P1 | Custom swipe | Custom swipe creation always fails. | FIXED_VERIFIED | backend/app/services/creative_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_custom_swipe_reference_integrity | None |
| F34 | P1 | Avatar | Avatar upload calls a nonexistent storage function. | FIXED_VERIFIED | backend/app/services/storage_service.py, backend/app/api/routers/account.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_storage_service_save_file_and_r2_validation | None |
| F35 | P1 | Frontend runtime | Performance crashes as soon as it has data. | FIXED_VERIFIED | src/pages/PerformancePage.jsx | npm run build && inspection of PerformancePage.jsx metrics useMemo. | None |
| F36 | P1 | Frontend runtime | Opening a nonempty notification menu crashes rendering. | FIXED_VERIFIED | src/components/NotificationBell.jsx | npm run build && component import audit. | None |
| F37 | P1 | Support | Support ticket listing fails once a ticket exists. | FIXED_VERIFIED | backend/app/services/support_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_support_ticket_batching_and_pagination | None |
| F38 | P1 | Gemini media | Every Gemini BYOK image call has an invalid argument. | FIXED_VERIFIED | backend/app/services/ai/gemini_provider.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_gemini_image_generation_kwargs | None |
| F39 | P1 | Media capabilities | Advertised media provider/mode capabilities are not wired through. | FIXED_VERIFIED | backend/app/services/provider_resolver.py, backend/app/services/ai/pollinations_provider.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_pollinations_and_provider_resolver | None |
| F40 | P1 | Media cancellation | Canceled media jobs can become completed and consume quota. | FIXED_VERIFIED | backend/app/services/media_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_media_generation_canceled_and_failure_handling | None |
| F41 | P1 | Insight persistence | Paid detailed insight fields disappear after reload. | FIXED_VERIFIED | backend/app/services/analysis_service.py, backend/app/schemas/analysis.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_insight_extended_fields_persistence_and_no_row_lock | None |
| F42 | P1 | Frontend false data | Intelligence invents output after errors and substitutes unrelated translations. | FIXED_VERIFIED | src/pages/IntelligencePage.jsx | Component test and code audit of IntelligencePage.jsx error handler. | None |
| F43 | P1 | Frontend false data | New accounts are given fictional search history. | FIXED_VERIFIED | src/context/SearchContext.jsx, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f12_f43_search_history_storage_isolation | None |
| F44 | P1 | Playbook wiring | The UI drops the search job ID when compiling a playbook. | FIXED_VERIFIED | src/context/SearchContext.jsx, src/pages/IntelligencePage.jsx, backend/tests/test_phase7_frontend_and_billing_suite.py | backend/tests/test_phase7_frontend_and_billing_suite.py::test_f44_playbook_compilation_preserves_job_id | None |
| F45 | P1 | Session loading | A transient session failure can leave the app loading forever. | FIXED_VERIFIED | src/context/AuthContext.jsx | AuthContext session state machine inspection & npm run build. | None |
| F46 | P1 | Teams | Team invitations report delivery but shared workspaces do not work. | FIXED_VERIFIED | backend/app/services/team_service.py, backend/app/core/tenancy.py, backend/app/services/billing_service.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f46_f47_team_management_rbac_and_invite_redemption | None |
| F47 | P1 | Team security | An invitation is not bound to its intended email or consumed atomically. | FIXED_VERIFIED | backend/app/services/team_service.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f46_f47_team_management_rbac_and_invite_redemption | None |
| F48 | P1 | Public updates | App-only updates are exposed by public APIs. | FIXED_VERIFIED | backend/app/api/routers/updates.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f48_updates_unauthenticated_public_filtering | None |
| F49 | P1 | Storage | Production media falls back to ephemeral storage on incomplete R2 configuration. | FIXED_VERIFIED | backend/app/services/storage_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_storage_service_save_file_and_r2_validation | None |
| F50 | P1 | Provider capacity | Twenty provider attempts disable discovery for every tenant. | FIXED_VERIFIED | backend/app/services/api_usage_service.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f50_org_scoped_api_usage_cap | None |
| F51 | P1 | Admin impersonation | The impersonation UI keeps using the administrator token. | FIXED_VERIFIED | src/pages/admin/UsersPage.jsx, src/services/http.js, backend/tests/test_phase7_frontend_and_billing_suite.py | backend/tests/test_phase7_frontend_and_billing_suite.py::test_f51_impersonation_token_identity | None |
| F52 | P1 | Default administrator | The admin seeder has a public fallback password. | FIXED_VERIFIED | backend/scripts/seed_admin.py | Inspection of backend/scripts/seed_admin.py. | None |
| F53 | P1 | Pattern generation | Pattern generation has shifted arguments, global data selection and no credit gate. | FIXED_VERIFIED | backend/app/services/creative_service.py, backend/app/api/routers/creatives.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f53_generate_patterns_validation_and_credit | None |
| F54 | P1 | Monitors | Provider outages can create false “ad stopped” alerts. | FIXED_VERIFIED | backend/app/services/monitor_service.py | monitor_service code audit verifying job.status == 'failed' or failure_kind == 'provider_outage' bypasses diff. | None |
| F55 | P1 | Plan limits | Configured per-plan image/video limits are ignored. | FIXED_VERIFIED | backend/app/services/discover_service.py, backend/tests/test_phase4_credits_quotas_suite.py | backend/tests/test_phase4_credits_quotas_suite.py::test_f11_f55_inflight_concurrency_and_per_plan_quotas | None |
| F56 | P1 | False metrics | Exported playbooks invent confidence and performance lift. | FIXED_VERIFIED | src/pages/DashboardPage.jsx | npm run build && DashboardPage.jsx compilation audit. | None |
| F57 | P1 | Frontend error states | Failed reads/saves are displayed as success, empty data or a waking server. | FIXED_VERIFIED | src/hooks/useLeadGenJob.js, src/pages/PerformancePage.jsx, src/services/http.js, backend/tests/test_phase7_frontend_and_billing_suite.py | backend/tests/test_phase7_frontend_and_billing_suite.py::test_f57_leadgen_worker_offline_structured_error | None |
| F79 | P1 | Billing completeness | Paid plans display “Monthly renewal” without a subscription lifecycle. | FIXED_VERIFIED | src/pages/BillingPage.jsx, backend/app/services/billing_service.py, backend/tests/test_phase7_frontend_and_billing_suite.py | backend/tests/test_phase7_frontend_and_billing_suite.py::test_f79_honest_subscription_lifecycle_and_no_fake_renewal | None |
| F80 | P1 | Admin authorization | Stored granular admin permissions do not restrict access. | FIXED_VERIFIED | backend/app/core/deps.py, backend/app/api/routers/admin.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f80_granular_admin_permissions | None |
| F81 | P1 | Leadgen capabilities | The XHR-capture option is accepted and stored but never implemented. | FIXED_VERIFIED | backend/app/services/scrapling_engine.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_scrapling_xhr_capture_with_ssrf_safety | None |
| F82 | P1 | Media stuck jobs | Provider-resolution failures leave media jobs pending indefinitely. | FIXED_VERIFIED | backend/app/services/media_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_media_generation_canceled_and_failure_handling | None |
| F58 | P2 | Rate limiting | Rate limits are spoofable in the app, instance-local and incomplete. | FIXED_VERIFIED | backend/app/middleware/rate_limit.py, backend/tests/test_phase8_security_and_resilience_suite.py | backend/tests/test_phase8_security_and_resilience_suite.py::test_f58_is_valid_public_ip, test_f58_client_ip_precedence, test_f58_rate_limit_rules_and_normalization | None |
| F59 | P2 | JWT key rotation | JWKS cache never refreshes. | FIXED_VERIFIED | backend/app/core/security.py | Unit test verifying TTL cache (_JWKS_CACHE_TTL_SECONDS = 3600.0) and force-refresh on key mismatch. | None |
| F60 | P2 | Password policy | Profile password changes bypass signup/reset length checks. | FIXED_VERIFIED | backend/app/api/routers/account.py, backend/tests/test_security_regressions.py | test_security_regressions.py | None |
| F61 | P2 | API entitlements | Issued API keys outlive the public_api entitlement and lose workspace scope. | FIXED_VERIFIED | backend/app/services/api_key_service.py, backend/app/core/deps.py, backend/app/core/tenancy.py, backend/tests/test_phase3_isolation_suite.py | backend/tests/test_phase3_isolation_suite.py::test_f61_api_key_entitlement_and_scoping | None |
| F62 | P2 | Database concurrency | Default-organization creation races. | FIXED_VERIFIED | backend/app/services/billing_service.py | billing_service savepoint retry logic. | None |
| F63 | P2 | Database performance | Hot tenant/job/filter queries lack supporting indexes. | FIXED_VERIFIED | backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py, backend/app/models/scrape_job.py, backend/app/models/creative.py, backend/app/models/leadgen.py | alembic check and schema inspection. | None |
| F64 | P2 | Query scaling | Several lists are unbounded; support adds an N+1 count query. | FIXED_VERIFIED | backend/app/services/support_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_support_ticket_batching_and_pagination | None |
| F65 | P2 | Request latency | LLM work holds an organization row lock inside a request. | FIXED_VERIFIED | backend/app/services/analysis_service.py, backend/tests/test_phase6_pipeline_integrity_suite.py | backend/tests/test_phase6_pipeline_integrity_suite.py::test_insight_extended_fields_persistence_and_no_row_lock | None |
| F66 | P2 | Network / memory | Fetch/upload paths have unbounded time, recursion or memory use. | FIXED_VERIFIED | backend/app/services/scrapling_engine.py, backend/app/services/leadgen_pipeline.py, backend/app/services/ai/pollinations_provider.py, backend/app/api/routers/media.py, backend/tests/test_phase8_security_and_resilience_suite.py | backend/tests/test_phase8_security_and_resilience_suite.py::test_f66_robots_allowed_ssrf_and_timeout, test_f66_parse_sitemap_recursion_and_visited_guards, test_f66_pollinations_streaming_chunk_limits | None |
| F67 | P2 | CSV export | Scraped strings can become spreadsheet formulas. | FIXED_VERIFIED | backend/app/api/routers/scout.py, backend/app/api/routers/leadgen.py, backend/tests/test_phase8_security_and_resilience_suite.py | backend/tests/test_phase8_security_and_resilience_suite.py::test_f67_csv_formula_injection_defense | None |
| F68 | P2 | Polling | Polling overlaps requests and stale failures can cancel a newer job. | FIXED_VERIFIED | src/hooks/useDiscoverySearch.js | Frontend build and timer lifecycle verification in npm run build. | None |
| F69 | P2 | Datetime contracts | Datetime serialization and scheduling lose timezone correctness. | FIXED_VERIFIED | backend/app/services/team_service.py, backend/app/api/routers/updates.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f69_format_utc_iso_no_double_offset, test_f69_normalize_to_utc_preserves_timestamp | None |
| F70 | P2 | Startup reconciliation | Starting another instance can fail a live long-running job. | FIXED_VERIFIED | backend/app/main.py | main.py reconciliation query inspection. | None |
| F71 | P2 | Analytics privacy | Unvalidated attribution can carry PII into analytics and logs. | FIXED_VERIFIED | src/lib/utm.js, src/pages/auth/SignUpPage.jsx, backend/app/services/auth_service.py, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f71_register_user_sanitizes_pii_from_attribution | None |
| F72 | P2 | Analytics attribution | Term/content-only UTM visits are dropped. | FIXED_VERIFIED | src/lib/utm.js, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f72_utm_file_verifies_term_content_condition | None |
| F73 | P2 | Accessibility | Keyboard/focus and label contracts are incomplete. | FIXED_VERIFIED | src/components/ui/ConfirmDialog.jsx, src/components/ui/Field.jsx, src/components/SavedDraftsModal.jsx, backend/tests/test_phase5_durable_jobs_suite.py | backend/tests/test_phase5_durable_jobs_suite.py::test_f73_accessibility_contracts_in_components | None |
| F74 | P2 | Deploy reproducibility | Backend/worker deploys resolve unbounded dependency versions. | FIXED_VERIFIED | backend/requirements.txt | requirements.txt inspection against pip freeze. | None |
| F75 | P2 | Production config | Invalid data-source configuration silently enables mock mode. | FIXED_VERIFIED | src/services/config.js | Frontend build and validation tests in npm run build. | None |
| F76 | P2 | Browser token storage | Long-lived bearer tokens are readable by every script on the origin. | FIXED_VERIFIED | src/services/api/authService.api.js | Static analysis of logout handlers and storage purging logic. | None |
| F77 | P3 | Schema consistency | Additional default/nullability differences make creation paths inconsistent. | FIXED_VERIFIED | backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py, backend/app/models/*.py | alembic check autogenerate comparison. | None |
| F78 | P3 | Code health | Generated artifacts, large modules and duplicated fallback/billing logic raise drift risk. | FIXED_VERIFIED | dist/index.html, backend/app/services/billing_service.py, backend/app/services/analysis_service.py | npm run build && full pytest suite across billing & analysis services. | None |
