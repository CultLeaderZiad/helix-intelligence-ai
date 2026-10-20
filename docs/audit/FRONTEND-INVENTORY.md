# جرد الواجهة الأمامية ومساراتها

> **ملخص الحالة:** ده جرد للـ frontend على مستوى الكود، ومعاه لقطات browser التقطها الـ parent على التطبيق المحلي بحساب Admin حقيقي وقاعدة بيانات disposable فاضية. Routes الـ public/auth اتصورت وإحنا signed out، وباقي صفحات التطبيق اتصورت بجلسة admin، بالإنجليزي والعربي. ما استخدمتش shared browser في الشغل ده.

> **Snapshot مهم:** كود التطبيق اللي اتراجع هو `eab70cc`، مش HEAD الحالي للفرع (`af5cdf9`) لأن الـ commits الأحدث توثيقية. المقارنة مع `main` على `5b45806`. مافيش app edits في المهمة دي.

الـ manifest فيه **68 مسار concrete**، وكل واحد له screenshot EN وAR (136 route/locale pairs). وفيه كمان حالات تفاعل إضافية؛ كل اللقطات مذكورة بالمسارات الفعلية للملفات ومربوطة تحت. `ok: true` معناه إن عملية الالتقاط تمت، مش ضمان إن الـ API رجّع بيانات أو إن الشاشة خلصت hydration.

## طريقة القراءة

- `real` معناها إن فيه implementation أو static content وservice path في الكود؛ مش إثبات نجاح live request. `partial` معناها جزء من التدفق موجود أو فيه اعتماد خارجي لسه غير متحقق. `empty` حالة not-found مقصودة. `mock` مصدر تجريبي قابل للاختيار في بيئات التطوير، ومش ناتج provider حقيقي. ما استخدمتش `broken` أو `dead` إلا لو فيه دليل مباشر كافي.
- الـ JSON التفصيلي فيه لكل مسار: `path`, `screenKey`, `kind`, `component`, `tabs`, selectors، source/API evidence وروابط اللقطات. القيم في `tabs` هي تبديلات محتوى/تبويبات فعلية؛ الفلاتر والـ actions موجودة تحت `controls` عشان ما نسميش كل فلتر tab.
- ملفات اللقطات تحت [`screens/`](screens/)، وبيانات الالتقاط الخام في [`evidence/browser-captures.jsonl`](evidence/browser-captures.jsonl). روابط EN/AR بالجدول بتوصل لاسم الصورة نفسه من الـ manifest.

## جرد المسارات واللقطات

الـ purpose والـ API calls والـ source status لكل route موجودين في [`frontend-routes.json`](evidence/frontend-routes.json). الجدول ده يربط كل concrete route بالـ component واللقطات الفعلية:

| Route | النوع | Component | EN | AR | Tabs/حالات UI |
|---|---|---|---|---|---|
| `/` | Public | `LandingPage` | [لقطة EN](../screens/landing-en.png) | [لقطة AR](../screens/landing-ar.png) | مفيش tabs |
| `/admin` | Admin | `OverviewPage` | [لقطة EN](../screens/admin-en.png) | [لقطة AR](../screens/admin-ar.png) | مفيش tabs; settled [EN](../screens/admin-tab-settled-en.png) [AR](../screens/admin-tab-settled-ar.png) |
| `/admin/access-requests` | Admin | `AccessRequestsPage` | [لقطة EN](../screens/admin-access-requests-en.png) | [لقطة AR](../screens/admin-access-requests-ar.png) | مفيش tabs |
| `/admin/audit-log` | Admin | `AuditLogPage` | [لقطة EN](../screens/admin-audit-log-en.png) | [لقطة AR](../screens/admin-audit-log-ar.png) | مفيش tabs |
| `/admin/data-sources` | Admin | `DataSourcesPage` | [لقطة EN](../screens/admin-data-sources-en.png) | [لقطة AR](../screens/admin-data-sources-ar.png) | مفيش tabs |
| `/admin/feature-flags` | Admin | `FeatureFlagsPage` | [لقطة EN](../screens/admin-feature-flags-en.png) | [لقطة AR](../screens/admin-feature-flags-ar.png) | مفيش tabs |
| `/admin/guide` | Admin | `GuidePage` | [لقطة EN](../screens/admin-guide-en.png) | [لقطة AR](../screens/admin-guide-ar.png) | Helix Architecture: The 4 Loops, Discover: Competitor Ad Extraction, Intelligence: Pattern Synthesis Teardowns, Create Studio: AI Generation, Performance: Longevity/Fatigue Tracking, Admin Center: Operations; Helix Architecture The 4 Loops [EN](../screens/admin-guide-tab-Helix-Architecture-The-4-Loops-en.png) [AR](../screens/admin-guide-tab-Helix-Architecture-The-4-Loops-ar.png); Discover Competitor Ad Extraction [EN](../screens/admin-guide-tab-Discover-Competitor-Ad-Extraction-en.png) [AR](../screens/admin-guide-tab-Discover-Competitor-Ad-Extraction-ar.png); Intelligence Pattern Synthesis Teardowns [EN](../screens/admin-guide-tab-Intelligence-Pattern-Synthesis-Teardowns-en.png) [AR](../screens/admin-guide-tab-Intelligence-Pattern-Synthesis-Teardowns-ar.png); Create Studio AI Generation [EN](../screens/admin-guide-tab-Create-Studio-AI-Generation-en.png) [AR](../screens/admin-guide-tab-Create-Studio-AI-Generation-ar.png); Performance Longevity Fatigue Tracking [EN](../screens/admin-guide-tab-Performance-Longevity-Fatigue-Tracking-en.png) [AR](../screens/admin-guide-tab-Performance-Longevity-Fatigue-Tracking-ar.png); Admin Center Operations [EN](../screens/admin-guide-tab-Admin-Center-Operations-en.png) [AR](../screens/admin-guide-tab-Admin-Center-Operations-ar.png) |
| `/admin/health` | Admin | `SystemHealthPage` | [لقطة EN](../screens/admin-health-en.png) | [لقطة AR](../screens/admin-health-ar.png) | مفيش tabs |
| `/admin/organizations` | Admin | `OrganizationsPage` | [لقطة EN](../screens/admin-organizations-en.png) | [لقطة AR](../screens/admin-organizations-ar.png) | مفيش tabs |
| `/admin/scrape-jobs` | Admin | `ScrapeJobsPage` | [لقطة EN](../screens/admin-scrape-jobs-en.png) | [لقطة AR](../screens/admin-scrape-jobs-ar.png) | مفيش tabs |
| `/admin/subscriptions` | Admin | `SubscriptionsPlansPage` | [لقطة EN](../screens/admin-subscriptions-en.png) | [لقطة AR](../screens/admin-subscriptions-ar.png) | مفيش tabs |
| `/admin/support` | Admin | `SupportAdminPage` | [لقطة EN](../screens/admin-support-en.png) | [لقطة AR](../screens/admin-support-ar.png) | مفيش tabs; All Types [EN](../screens/admin-support-tab-All-Types-en.png) [AR](../screens/admin-support-tab-All-Types-ar.png); All Statuses [EN](../screens/admin-support-tab-All-Statuses-en.png) [AR](../screens/admin-support-tab-All-Statuses-ar.png); Open [EN](../screens/admin-support-tab-Open-en.png) [AR](../screens/admin-support-tab-Open-ar.png); In Progress [EN](../screens/admin-support-tab-In-Progress-en.png) [AR](../screens/admin-support-tab-In-Progress-ar.png); Resolved [EN](../screens/admin-support-tab-Resolved-en.png) [AR](../screens/admin-support-tab-Resolved-ar.png); Bug Reports [EN](../screens/admin-support-tab-Bug-Reports-en.png) [AR](../screens/admin-support-tab-Bug-Reports-ar.png); Feedback Ideas [EN](../screens/admin-support-tab-Feedback-Ideas-en.png) [AR](../screens/admin-support-tab-Feedback-Ideas-ar.png); Support [EN](../screens/admin-support-tab-Support-en.png) [AR](../screens/admin-support-tab-Support-ar.png) |
| `/admin/updates` | Admin | `UpdatesPage` | [لقطة EN](../screens/admin-updates-en.png) | [لقطة AR](../screens/admin-updates-ar.png) | Editor, Preview; new editor [EN](../screens/admin-updates-tab-new-editor-en.png) [AR](../screens/admin-updates-tab-new-editor-ar.png); preview [EN](../screens/admin-updates-tab-preview-en.png) [AR](../screens/admin-updates-tab-preview-ar.png); editor [EN](../screens/admin-updates-tab-editor-en.png) [AR](../screens/admin-updates-tab-editor-ar.png) |
| `/admin/usage` | Admin | `UsagePage` | [لقطة EN](../screens/admin-usage-en.png) | [لقطة AR](../screens/admin-usage-ar.png) | مفيش tabs; settled [EN](../screens/admin-usage-tab-settled-en.png) [AR](../screens/admin-usage-tab-settled-ar.png) |
| `/admin/users` | Admin | `UsersPage` | [لقطة EN](../screens/admin-users-en.png) | [لقطة AR](../screens/admin-users-ar.png) | مفيش tabs |
| `/api-keys` | Workspace بعد تسجيل الدخول | `ApiKeysPage` | [لقطة EN](../screens/api-keys-en.png) | [لقطة AR](../screens/api-keys-ar.png) | مفيش tabs; spa navigation [EN](../screens/api-keys-tab-spa-navigation-en.png) [AR](../screens/api-keys-tab-spa-navigation-ar.png) |
| `/billing` | Workspace بعد تسجيل الدخول | `BillingPage` | [لقطة EN](../screens/billing-en.png) | [لقطة AR](../screens/billing-ar.png) | مفيش tabs |
| `/cookies` | Public | `LegalPage` | [لقطة EN](../screens/cookies-en.png) | [لقطة AR](../screens/cookies-ar.png) | مفيش tabs |
| `/create` | Workspace بعد تسجيل الدخول | `CreatePage` | [لقطة EN](../screens/create-en.png) | [لقطة AR](../screens/create-ar.png) | Image Creative, Video Motion; Image Creative [EN](../screens/create-tab-Image-Creative-en.png) [AR](../screens/create-tab-Image-Creative-ar.png); Video Motion [EN](../screens/create-tab-Video-Motion-en.png) [AR](../screens/create-tab-Video-Motion-ar.png); Image Creative Quick Concept [EN](../screens/create-tab-Image-Creative-Quick-Concept-en.png) [AR](../screens/create-tab-Image-Creative-Quick-Concept-ar.png); Image Creative Commercial Ad Still [EN](../screens/create-tab-Image-Creative-Commercial-Ad-Still-en.png) [AR](../screens/create-tab-Image-Creative-Commercial-Ad-Still-ar.png); Image Creative Storyboard Frame [EN](../screens/create-tab-Image-Creative-Storyboard-Frame-en.png) [AR](../screens/create-tab-Image-Creative-Storyboard-Frame-ar.png); Image Creative Graphic Layout [EN](../screens/create-tab-Image-Creative-Graphic-Layout-en.png) [AR](../screens/create-tab-Image-Creative-Graphic-Layout-ar.png); Video Motion Ad Concept Short [EN](../screens/create-tab-Video-Motion-Ad-Concept-Short-en.png) [AR](../screens/create-tab-Video-Motion-Ad-Concept-Short-ar.png); Video Motion Explainer [EN](../screens/create-tab-Video-Motion-Explainer-en.png) [AR](../screens/create-tab-Video-Motion-Explainer-ar.png); Video Motion UGC Clip [EN](../screens/create-tab-Video-Motion-UGC-Clip-en.png) [AR](../screens/create-tab-Video-Motion-UGC-Clip-ar.png) |
| `/dashboard` | Workspace بعد تسجيل الدخول | `DashboardPage` | [لقطة EN](../screens/dashboard-en.png) | [لقطة AR](../screens/dashboard-ar.png) | مفيش tabs; settled [EN](../screens/dashboard-tab-settled-en.png) [AR](../screens/dashboard-tab-settled-ar.png) |
| `/discover` | Workspace بعد تسجيل الدخول | `DiscoverPage` | [لقطة EN](../screens/discover-en.png) | [لقطة AR](../screens/discover-ar.png) | مفيش tabs; filters [EN](../screens/discover-tab-filters-en.png) [AR](../screens/discover-tab-filters-ar.png); drafts history [EN](../screens/discover-tab-drafts-history-en.png) [AR](../screens/discover-tab-drafts-history-ar.png) |
| `/docs` | Docs | `DocsHomePage` | [لقطة EN](../screens/docs-en.png) | [لقطة AR](../screens/docs-ar.png) | مفيش tabs |
| `/docs/api-reference` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-en.png) | [لقطة AR](../screens/docs-api-reference-ar.png) | مفيش tabs |
| `/docs/api-reference/authentication` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-authentication-en.png) | [لقطة AR](../screens/docs-api-reference-authentication-ar.png) | مفيش tabs |
| `/docs/api-reference/credit-costs-and-limits` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-credit-costs-and-limits-en.png) | [لقطة AR](../screens/docs-api-reference-credit-costs-and-limits-ar.png) | مفيش tabs |
| `/docs/api-reference/endpoint-creatives` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-endpoint-creatives-en.png) | [لقطة AR](../screens/docs-api-reference-endpoint-creatives-ar.png) | مفيش tabs |
| `/docs/api-reference/endpoint-discover` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-endpoint-discover-en.png) | [لقطة AR](../screens/docs-api-reference-endpoint-discover-ar.png) | مفيش tabs |
| `/docs/api-reference/endpoint-media-generate` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-endpoint-media-generate-en.png) | [لقطة AR](../screens/docs-api-reference-endpoint-media-generate-ar.png) | مفيش tabs |
| `/docs/api-reference/endpoint-monitors` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-api-reference-endpoint-monitors-en.png) | [لقطة AR](../screens/docs-api-reference-endpoint-monitors-ar.png) | مفيش tabs |
| `/docs/scout-cli` | Docs | `ScoutCliDocsPage` | [لقطة EN](../screens/docs-scout-cli-en.png) | [لقطة AR](../screens/docs-scout-cli-ar.png) | مفيش tabs |
| `/docs/user-guide` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-en.png) | [لقطة AR](../screens/docs-user-guide-ar.png) | مفيش tabs |
| `/docs/user-guide/concept-audience-simulation` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-concept-audience-simulation-en.png) | [لقطة AR](../screens/docs-user-guide-concept-audience-simulation-ar.png) | مفيش tabs |
| `/docs/user-guide/concept-competitor-monitors` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-concept-competitor-monitors-en.png) | [لقطة AR](../screens/docs-user-guide-concept-competitor-monitors-ar.png) | مفيش tabs |
| `/docs/user-guide/concept-estimated-vs-real-data` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-concept-estimated-vs-real-data-en.png) | [لقطة AR](../screens/docs-user-guide-concept-estimated-vs-real-data-ar.png) | مفيش tabs |
| `/docs/user-guide/concept-how-discover-works` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-concept-how-discover-works-en.png) | [لقطة AR](../screens/docs-user-guide-concept-how-discover-works-ar.png) | مفيش tabs |
| `/docs/user-guide/concept-scoring-system` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-concept-scoring-system-en.png) | [لقطة AR](../screens/docs-user-guide-concept-scoring-system-ar.png) | مفيش tabs |
| `/docs/user-guide/faq` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-faq-en.png) | [لقطة AR](../screens/docs-user-guide-faq-ar.png) | مفيش tabs |
| `/docs/user-guide/lead-generation` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-lead-generation-en.png) | [لقطة AR](../screens/docs-user-guide-lead-generation-ar.png) | مفيش tabs |
| `/docs/user-guide/quickstart-account-and-trial` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-quickstart-account-and-trial-en.png) | [لقطة AR](../screens/docs-user-guide-quickstart-account-and-trial-ar.png) | مفيش tabs |
| `/docs/user-guide/quickstart-credits-and-limits` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-quickstart-credits-and-limits-en.png) | [لقطة AR](../screens/docs-user-guide-quickstart-credits-and-limits-ar.png) | مفيش tabs |
| `/docs/user-guide/quickstart-first-search` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-quickstart-first-search-en.png) | [لقطة AR](../screens/docs-user-guide-quickstart-first-search-ar.png) | مفيش tabs |
| `/docs/user-guide/quickstart-reading-intelligence` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-quickstart-reading-intelligence-en.png) | [لقطة AR](../screens/docs-user-guide-quickstart-reading-intelligence-ar.png) | مفيش tabs |
| `/docs/user-guide/quickstart-remix-studio` | Docs | `DocsDetailPage` | [لقطة EN](../screens/docs-user-guide-quickstart-remix-studio-en.png) | [لقطة AR](../screens/docs-user-guide-quickstart-remix-studio-ar.png) | مفيش tabs |
| `/forgot-password` | Auth / برا التطبيق | `ForgotPasswordPage` | [لقطة EN](../screens/forgot-password-en.png) | [لقطة AR](../screens/forgot-password-ar.png) | مفيش tabs |
| `/guide` | Workspace بعد تسجيل الدخول | `GuidePage` | [لقطة EN](../screens/guide-en.png) | [لقطة AR](../screens/guide-ar.png) | Helix Architecture: The 4 Loops, Discover: Competitor Ad Extraction, Intelligence: Pattern Synthesis Teardowns, Create Studio: AI Generation, Performance: Longevity/Fatigue Tracking, Admin Center: Operations; Helix Architecture The 4 Loops [EN](../screens/guide-tab-Helix-Architecture-The-4-Loops-en.png) [AR](../screens/guide-tab-Helix-Architecture-The-4-Loops-ar.png); Discover Competitor Ad Extraction [EN](../screens/guide-tab-Discover-Competitor-Ad-Extraction-en.png) [AR](../screens/guide-tab-Discover-Competitor-Ad-Extraction-ar.png); Intelligence Pattern Synthesis Teardowns [EN](../screens/guide-tab-Intelligence-Pattern-Synthesis-Teardowns-en.png) [AR](../screens/guide-tab-Intelligence-Pattern-Synthesis-Teardowns-ar.png); Create Studio AI Generation [EN](../screens/guide-tab-Create-Studio-AI-Generation-en.png) [AR](../screens/guide-tab-Create-Studio-AI-Generation-ar.png); Performance Longevity Fatigue Tracking [EN](../screens/guide-tab-Performance-Longevity-Fatigue-Tracking-en.png) [AR](../screens/guide-tab-Performance-Longevity-Fatigue-Tracking-ar.png); Admin Center Operations [EN](../screens/guide-tab-Admin-Center-Operations-en.png) [AR](../screens/guide-tab-Admin-Center-Operations-ar.png) |
| `/intelligence` | Workspace بعد تسجيل الدخول | `IntelligencePage` | [لقطة EN](../screens/intelligence-en.png) | [لقطة AR](../screens/intelligence-ar.png) | مفيش tabs |
| `/legal` | Public | `LegalPage` | [لقطة EN](../screens/legal-en.png) | [لقطة AR](../screens/legal-ar.png) | مفيش tabs |
| `/legal/privacy` | Public | `LegalPage` | [لقطة EN](../screens/legal-privacy-en.png) | [لقطة AR](../screens/legal-privacy-ar.png) | مفيش tabs |
| `/monitors` | Workspace بعد تسجيل الدخول | `MonitorsPage` | [لقطة EN](../screens/monitors-en.png) | [لقطة AR](../screens/monitors-ar.png) | مفيش tabs |
| `/not-a-real-route` | Not Found | `NotFoundPage` | [لقطة EN](../screens/not-a-real-route-en.png) | [لقطة AR](../screens/not-a-real-route-ar.png) | مفيش tabs |
| `/notifications` | Workspace بعد تسجيل الدخول | `NotificationsPage` | [لقطة EN](../screens/notifications-en.png) | [لقطة AR](../screens/notifications-ar.png) | All, Unread, Announcements, Alerts; All [EN](../screens/notifications-tab-All-en.png) [AR](../screens/notifications-tab-All-ar.png); Unread [EN](../screens/notifications-tab-Unread-en.png) [AR](../screens/notifications-tab-Unread-ar.png); Announcements [EN](../screens/notifications-tab-Announcements-en.png) [AR](../screens/notifications-tab-Announcements-ar.png); Alerts [EN](../screens/notifications-tab-Alerts-en.png) [AR](../screens/notifications-tab-Alerts-ar.png) |
| `/performance` | Workspace بعد تسجيل الدخول | `PerformancePage` | [لقطة EN](../screens/performance-en.png) | [لقطة AR](../screens/performance-ar.png) | مفيش tabs |
| `/playbook/audit-not-found` | Public | `PublicPlaybookPage` | [لقطة EN](../screens/playbook-audit-not-found-en.png) | [لقطة AR](../screens/playbook-audit-not-found-ar.png) | مفيش tabs |
| `/privacy` | Public | `LegalPage` | [لقطة EN](../screens/privacy-en.png) | [لقطة AR](../screens/privacy-ar.png) | مفيش tabs |
| `/reset-password` | Auth / برا التطبيق | `ResetPasswordPage` | [لقطة EN](../screens/reset-password-en.png) | [لقطة AR](../screens/reset-password-ar.png) | مفيش tabs |
| `/scout` | Redirect | `Navigate → /scout/social` | [لقطة EN](../screens/scout-en.png) | [لقطة AR](../screens/scout-ar.png) | مفيش tabs |
| `/scout/lead-generation` | Workspace بعد تسجيل الدخول | `ScoutLeadGenerationPage` | [لقطة EN](../screens/scout-lead-generation-en.png) | [لقطة AR](../screens/scout-lead-generation-ar.png) | مفيش tabs |
| `/scout/maps` | Workspace بعد تسجيل الدخول | `ScoutPage` | [لقطة EN](../screens/scout-maps-en.png) | [لقطة AR](../screens/scout-maps-ar.png) | Active Workspace, Org Social Jobs, Org Maps Jobs; Active Workspace [EN](../screens/scout-maps-tab-Active-Workspace-en.png) [AR](../screens/scout-maps-tab-Active-Workspace-ar.png); Org Social Jobs [EN](../screens/scout-maps-tab-Org-Social-Jobs-en.png) [AR](../screens/scout-maps-tab-Org-Social-Jobs-ar.png); Org Maps Jobs [EN](../screens/scout-maps-tab-Org-Maps-Jobs-en.png) [AR](../screens/scout-maps-tab-Org-Maps-Jobs-ar.png) |
| `/scout/social` | Workspace بعد تسجيل الدخول | `ScoutPage` | [لقطة EN](../screens/scout-social-en.png) | [لقطة AR](../screens/scout-social-ar.png) | Active Workspace, Org Social Jobs, Org Maps Jobs; Active Workspace [EN](../screens/scout-social-tab-Active-Workspace-en.png) [AR](../screens/scout-social-tab-Active-Workspace-ar.png); Org Social Jobs [EN](../screens/scout-social-tab-Org-Social-Jobs-en.png) [AR](../screens/scout-social-tab-Org-Social-Jobs-ar.png); Org Maps Jobs [EN](../screens/scout-social-tab-Org-Maps-Jobs-en.png) [AR](../screens/scout-social-tab-Org-Maps-Jobs-ar.png) |
| `/settings` | Workspace بعد تسجيل الدخول | `ProfileSettingsPage` | [لقطة EN](../screens/settings-en.png) | [لقطة AR](../screens/settings-ar.png) | مفيش tabs |
| `/sign-in` | Auth / برا التطبيق | `SignInPage` | [لقطة EN](../screens/sign-in-en.png) | [لقطة AR](../screens/sign-in-ar.png) | مفيش tabs |
| `/sign-up` | Auth / برا التطبيق | `SignUpPage` | [لقطة EN](../screens/sign-up-en.png) | [لقطة AR](../screens/sign-up-ar.png) | مفيش tabs |
| `/support` | Workspace بعد تسجيل الدخول | `SupportPage` | [لقطة EN](../screens/support-en.png) | [لقطة AR](../screens/support-ar.png) | مفيش tabs |
| `/swipe-files` | Workspace بعد تسجيل الدخول | `SwipeFilesPage` | [لقطة EN](../screens/swipe-files-en.png) | [لقطة AR](../screens/swipe-files-ar.png) | مفيش tabs |
| `/team` | Workspace بعد تسجيل الدخول | `TeamPage` | [لقطة EN](../screens/team-en.png) | [لقطة AR](../screens/team-ar.png) | مفيش tabs |
| `/team/accept` | Workspace بعد تسجيل الدخول | `TeamAcceptPage` | [لقطة EN](../screens/team-accept-en.png) | [لقطة AR](../screens/team-accept-ar.png) | مفيش tabs |
| `/terms` | Public | `LegalPage` | [لقطة EN](../screens/terms-en.png) | [لقطة AR](../screens/terms-ar.png) | مفيش tabs |
| `/updates` | Public | `PublicUpdatesPage` | [لقطة EN](../screens/updates-en.png) | [لقطة AR](../screens/updates-ar.png) | مفيش tabs |

## تبويبات وفلاتر لازم تتجرّب

الـ selector المكتوب في JSON قابل للاستخدام كبداية في browser automation. عناصر التبديل دي أزرار/local state، ومش ظاهر إنها بتستخدم `role="tab"`/`tablist` بشكل دلالي في المصدر. الحالات المصوّرة مربوطة في عمود المسار فوق، وبرضه مجمعة هنا حسب الشاشة:

| الشاشة | Tabs / controls | الملاحظة |
|---|---|---|
| `/notifications` | Tabs: All, Unread, Announcements, Alerts |; captures: All, Unread, Announcements, Alerts |
| `/create` | Tabs: Image Creative, Video Motion |; captures: Image Creative, Video Motion, Image Creative Quick Concept, Image Creative Commercial Ad Still, Image Creative Storyboard Frame, Image Creative Graphic Layout, Video Motion Ad Concept Short, Video Motion Explainer, Video Motion UGC Clip |
| `/performance` | Controls: All Formats, video, image, Any Duration, ≥7d, ≥14d, ≥30d, Search competitor or brand | |
| `/scout/social` | Tabs: Active Workspace, Org Social Jobs, Org Maps Jobs |; captures: Active Workspace, Org Social Jobs, Org Maps Jobs |
| `/scout/maps` | Tabs: Active Workspace, Org Social Jobs, Org Maps Jobs |; captures: Active Workspace, Org Social Jobs, Org Maps Jobs |
| `/guide` | Tabs: Helix Architecture: The 4 Loops, Discover: Competitor Ad Extraction, Intelligence: Pattern Synthesis Teardowns, Create Studio: AI Generation, Performance: Longevity/Fatigue Tracking, Admin Center: Operations |; captures: Helix Architecture The 4 Loops, Discover Competitor Ad Extraction, Intelligence Pattern Synthesis Teardowns, Create Studio AI Generation, Performance Longevity Fatigue Tracking, Admin Center Operations |
| `/admin/guide` | Tabs: Helix Architecture: The 4 Loops, Discover: Competitor Ad Extraction, Intelligence: Pattern Synthesis Teardowns, Create Studio: AI Generation, Performance: Longevity/Fatigue Tracking, Admin Center: Operations |; captures: Helix Architecture The 4 Loops, Discover Competitor Ad Extraction, Intelligence Pattern Synthesis Teardowns, Create Studio AI Generation, Performance Longevity Fatigue Tracking, Admin Center Operations |
| `/settings` | Controls: Profile photo upload, Save Settings, Change password |; مفيش tabs؛ دي forms/flows. |
| `/support` | Controls: Create support ticket, Reply to ticket |; مفيش tabs؛ دي forms/flows. |
| `/admin/support` | Controls: Status: All Statuses / Open / In Progress / Resolved, Type: All Types / Bug Reports / Feedback Ideas / Support, Refresh |; captures: All Types, All Statuses, Open, In Progress, Resolved, Bug Reports, Feedback Ideas, Support |
| `/admin/usage` | Controls: Provider filter, Search usage |; captures: settled |
| `/admin/audit-log` | Controls: Provider filter, Operation filter, User filter | |
| `/admin/scrape-jobs` | Controls: All, Queued, Running, Completed, Failed | |
| `/admin/updates` | Tabs: Editor, Preview; Controls: New Update, Publish, Save Draft |; captures: new editor, preview, editor |
| `/admin/data-sources` | Controls: Probe All Sources |; `activeTab` state موجودة لكن مفيش UI tab مربوط بيها. |

## ملاحظات من الـ browser captures

- اللقطات اتعملت على local app ببيانات admin حقيقية وجلسة تسجيل فعلية، مع disposable empty DB؛ مافيش fake data اتضافت. وجود empty DB يفسر empty states، ومش دليل على فشل الخدمة.
- `/api-keys` في الـ direct deep link رجّع backend `{"detail":"Not Found"}` حسب capture `api-keys-en.png` (واللقطة العربية المقابلة موجودة). الـ Vite proxy عنده prefix `/api` فـ `/api-keys` بيتلقط كأنه مسار API. فيه capture منفصل باسم variant `spa-navigation` للتنقل داخل React؛ لازم نقارن المسارين وما نعممش نتيجة direct link على component نفسه.
- `/admin` و`/dashboard` كان شكلهم لسه loading بعد ثانية واحدة. ده snapshot قصير، مش دليل مستمر إنهم broken؛ محتاجين انتظار أطول/re-check قبل توصيفهم.
- كل الـ 136 route/locale pairs اللي في manifest موجودة ومعلمة `ok: true`. ده نجاح capture بس؛ مش تأكيد لنجاح API، اكتمال hydration، صحة provider، أو persistence.

## ملاحظات المصدر: navigation والـ maturity

- `README.md:9-12` بيقول إن Discover هو loop الوحيد end-to-end وإن باقي sidebar placeholders، لكن الشجرة الحالية فيها صفحات وخدمات حقيقية أكتر من كده. `ARCHITECTURE.md:10-13` كمان بيقول Create live، بينما README بيحطه ضمن المخطط. و`src/app/navigation.js:15-55` معلّم الست أقسام الأساسية `live`. لازم product status copy يتفق مع اللي متحقق فعلاً في التطبيق.
- Discover عنده مسار jobs/results واضح: `/discovery/jobs`, `/discovery/jobs/{id}`, `/discovery/jobs/{id}/results`. الـ brief السابق ذكر إن production كان بيقف عند “resolving sources”، لكن اللقطة المحلية على DB فاضية مش إعادة إنتاج للمشكلة دي.
- Intelligence وCreate وPerformance عندهم components/services، لكن وجود wiring مش معناه إن مصادر/provider أو النتيجة end-to-end متأكدين. خلّي Discover هو الوعد الأساسي المتحقق، وخلي maturity labels صريحة لباقي loops بدل كلمة live العامة.
- `/guide`, `/admin/guide`, `/docs` وpublic playbooks متداخلين في التسميات والغرض. وضّح الفرق بين user guide وadmin operating playbook والـ API docs.
- `/scout` redirect إلى `/scout/social`; `/scout/:mode` dynamic واسع. خلي unsupported modes تروح لحالة واضحة بدل ما تظهر mode افتراضي بصمت.
- `AdminPendingPage` scaffold موجود لكنه مش مربوط بأي route. ما ينفعش نستنتج منه إن admin pages الموصولة كلها placeholders.

## Billing والشفافية القانونية

- صفحة `/billing` بتعرض usage/access وطلب صلاحية؛ المصادر بتوصف access يدوي من Admin ومفيش checkout provider أو flow شراء ظاهر. خليها صفحة usage/access واضحة، وخبّي trial countdown أو ادعاء شراء خطة لحد ما يتوفر backend/payment flow مطابق.
- صفحة `/admin/subscriptions` إدارة داخلية لـ plans/entitlements مش دليل على وجود دفع فعلي. نفس الفصل لازم ينعكس في docs والـ marketing.
- حافظ على disclosures واضحة إن بعض signals تقديرية أو ناتجة عن AI، وإن availability بتاعة integrations لازم تتعرض من health result حقيقي. Legal docs الحالية محتاجة مراجعة/اعتماد بشري قبل تقديمها كسياسة قانونية نهائية.

## API services والـ mocks

- service boundary: `src/services/index.js`; API modules في `src/services/api/`; mocks في `src/services/mock/`; النقل المشترك في `src/services/http.js`. `VITE_DATA_SOURCE` افتراضه API، وproduction build بيرفض mock. وجود service path مش إثبات response live.
- أهم families: `/auth/*`, `/account/*`, `/admin/*`, `/discovery/jobs*`, `/creatives*`, `/patterns*`, `/insights*`, `/media/jobs*`, `/scout/*`, `/monitors*`, `/notifications*`, `/dashboard/metrics`, `/playbooks*`, `/support/tickets*`, `/updates*`. الـ per-route API lists في JSON evidence.
- `DataSourcesPage` fallback بيعرض “Operational & Available in failover stack” لمصدر مش متطابق مع provider record؛ ده ممكن يوحي إن الخدمة سليمة بلا دليل. اعرض “status unavailable” لما مفيش health result محدد.
- `/admin/audit-log` موصول بـ `/admin/usage/logs` وفلاتر provider/operation/user؛ لاحظ إن user filter مش dependency في effect حسب المصدر، فالتغيير ممكن ما يحمّلش تلقائياً إلا عند submit.

## EN/AR وRTL

- `LanguageContext` يبدّل `document.lang` و`document.dir`، وفيه قاموس EN/AR. اللقطات المرفقة دليل مرئي للحالة المتصورة بس، مش ضمان إن كل copy أو كل component مترجم.
- لسه فيه نصوص إنجليزية مباشرة في Intelligence (`src/pages/IntelligencePage.jsx:480`)، Create (`:541,551,592`)، Monitors (`:128`)، Support (`:265`) وPerformance (`:329`). Dynamic content عنده `dir="auto"` في أماكن محددة بس. راجع bidi للأرقام والروابط والنص المختلط داخل forms/tables/dialogs على أحجام شاشة مختلفة.
- أزرار الصفحات المكتشفة مش مُمثلة كـ ARIA tabs؛ اختبر keyboard navigation وfocus وإعلانات screen reader، خصوصاً في Notifications وScout وUpdates والـ guide topic selectors.

## النتيجة وحدود التحقق

- اتراجع source snapshot `eab70cc` بس؛ فرع docs HEAD اتسجل منفصل. ملفات app مالمستهاش في المهمة دي.
- الـ browser screenshots والـ manifest ملاحظات parent-observed؛ المصدر/API statements تفضل source-only supplement إلا لو اللقطة أثبتت النص/الحالة بصرياً. مافيش اتصال بproduction، provider credentials، أو production DB.
- لسه غير متحقق: هل `/admin` و`/dashboard` بيخلصوا loading بعد انتظار أطول؛ نجاح API/provider على بيانات حقيقية؛ سلوك `/api-keys` deep link خارج إعداد Vite المحلي؛ tenant isolation/persistence؛ accessibility التفاعلية beyond اللي ظاهر في capture.
- أولوية متابعة واحدة: أصلح direct deep-link routing تحت Vite/hosting من غير ما تكسر `/api/*` proxy، وبعدها أعد فحص `/api-keys` direct وSPA navigation كمسارين منفصلين.
