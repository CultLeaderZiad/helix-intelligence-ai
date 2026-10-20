# جرد الـbrowser الفعلي — EN / AR + RTL

كود W4: `eab70cc`. **68 concrete paths**، و**136 route/locale screenshots**. إجمالي **240 screenshots** صالحة موجودة؛ الـraw log فيه محاولات أقدم/غير متطابقة محفوظة للتتبّع مش counted كنجاح.

البيانات من local empty/disposable DB، ومفيش provider output أو populated-detail records. Status الكود مش ضمان outcome؛ صورة loading مش terminal success. وصف `empty/partial` مش `mock` إلا لو config فعلًا mock، والـAPI هنا `USE_MOCKS=false`.

لقطات التابات/الـmodes وpending access تحت جدول الصفحات. تفاصيل source/status في [FRONTEND-INVENTORY](FRONTEND-INVENTORY.md).

| Path | الوظيفة / المكونات | Status مرصود | Endpoints من source | EN | AR |
|---|---|---|---|---|---|
| `/` | Marketing landing and product CTA — `` | partial | static / shared auth+chrome calls | [لقطة](screens/landing-en.png) | [لقطة](screens/landing-ar.png) |
| `/admin` | Operations overview — `` | initial loading; see settled capture if available | GET /admin/overview/stats | [لقطة](screens/admin-en.png) | [لقطة](screens/admin-ar.png) |
| `/admin/access-requests` | Review, grant, or reject access requests — `` | partial | /admin/access-requests | [لقطة](screens/admin-access-requests-en.png) | [لقطة](screens/admin-access-requests-ar.png) |
| `/admin/audit-log` | Administrative audit events — `` | initial loading; see settled capture if available | GET /admin/usage/logs?page=&page_size=30&provider=&operation=&user_id= | [لقطة](screens/admin-audit-log-en.png) | [لقطة](screens/admin-audit-log-ar.png) |
| `/admin/data-sources` | Provider/ingestion health — `` | partial | GET /admin/system/health | [لقطة](screens/admin-data-sources-en.png) | [لقطة](screens/admin-data-sources-ar.png) |
| `/admin/feature-flags` | Feature flag controls — `` | partial | /admin feature-flag actions | [لقطة](screens/admin-feature-flags-en.png) | [لقطة](screens/admin-feature-flags-ar.png) |
| `/admin/guide` | Operating playbook — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/admin-guide-en.png) | [لقطة](screens/admin-guide-ar.png) |
| `/admin/health` | System health — `` | partial | GET /admin/system/health | [لقطة](screens/admin-health-en.png) | [لقطة](screens/admin-health-ar.png) |
| `/admin/organizations` | Organization operations — `` | partial | /admin/organizations and organization actions | [لقطة](screens/admin-organizations-en.png) | [لقطة](screens/admin-organizations-ar.png) |
| `/admin/scrape-jobs` | Scrape job operations — `` | empty / API outcome not provider-verified | /admin/jobs | [لقطة](screens/admin-scrape-jobs-en.png) | [لقطة](screens/admin-scrape-jobs-ar.png) |
| `/admin/subscriptions` | Internal plans and subscription administration — `` | partial | /admin/plans | [لقطة](screens/admin-subscriptions-en.png) | [لقطة](screens/admin-subscriptions-ar.png) |
| `/admin/support` | Support ticket queue — `` | empty / API outcome not provider-verified | /admin/support/tickets | [لقطة](screens/admin-support-en.png) | [لقطة](screens/admin-support-ar.png) |
| `/admin/updates` | Update/banners editor and preview — `` | empty / API outcome not provider-verified | /updates/admin; /updates/admin/all; /updates/banner; /updates/admin/{id} | [لقطة](screens/admin-updates-en.png) | [لقطة](screens/admin-updates-ar.png) |
| `/admin/usage` | Usage and metering — `` | initial loading; see settled capture if available | /admin/usage; /admin/usage/logs | [لقطة](screens/admin-usage-en.png) | [لقطة](screens/admin-usage-ar.png) |
| `/admin/users` | User administration — `` | partial | /admin/users and user actions | [لقطة](screens/admin-users-en.png) | [لقطة](screens/admin-users-ar.png) |
| `/api-keys` | Workspace API key management — `` | broken direct dev load; SPA partial/loaded | /account/api-keys; workspace provider request | [لقطة](screens/api-keys-en.png) | [لقطة](screens/api-keys-ar.png) |
| `/billing` | Plan, usage, credits and access requests — `` | initial loading; see settled capture if available | GET /account/billing; GET /account/usage/today; GET /account/access; /account/access-requests | [لقطة](screens/billing-en.png) | [لقطة](screens/billing-ar.png) |
| `/cookies` | Cookie information alias using LegalPage — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/cookies-en.png) | [لقطة](screens/cookies-ar.png) |
| `/create` | Creative remix and media generation — `` | partial | GET /creatives/{id}; POST /media/jobs; GET /media/jobs/{id} | [لقطة](screens/create-en.png) | [لقطة](screens/create-ar.png) |
| `/dashboard` | Workspace metrics and playbook compilation — `` | partial | GET /dashboard/metrics; /playbooks | [لقطة](screens/dashboard-en.png) | [لقطة](screens/dashboard-ar.png) |
| `/discover` | Competitive ad search and results — `` | empty / API outcome not provider-verified | POST /discovery/jobs; GET /discovery/jobs/{id}; GET /discovery/jobs/{id}/results | [لقطة](screens/discover-en.png) | [لقطة](screens/discover-ar.png) |
| `/docs` | Documentation index — `` | empty / API outcome not provider-verified | static / shared auth+chrome calls | [لقطة](screens/docs-en.png) | [لقطة](screens/docs-ar.png) |
| `/docs/api-reference` | First registered article in a docs section — `` | redirect → /docs/api-reference/authentication | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-en.png) | [لقطة](screens/docs-api-reference-ar.png) |
| `/docs/api-reference/authentication` | Registered static Markdown article — `` | empty / API outcome not provider-verified | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-authentication-en.png) | [لقطة](screens/docs-api-reference-authentication-ar.png) |
| `/docs/api-reference/credit-costs-and-limits` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-credit-costs-and-limits-en.png) | [لقطة](screens/docs-api-reference-credit-costs-and-limits-ar.png) |
| `/docs/api-reference/endpoint-creatives` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-endpoint-creatives-en.png) | [لقطة](screens/docs-api-reference-endpoint-creatives-ar.png) |
| `/docs/api-reference/endpoint-discover` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-endpoint-discover-en.png) | [لقطة](screens/docs-api-reference-endpoint-discover-ar.png) |
| `/docs/api-reference/endpoint-media-generate` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-endpoint-media-generate-en.png) | [لقطة](screens/docs-api-reference-endpoint-media-generate-ar.png) |
| `/docs/api-reference/endpoint-monitors` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-api-reference-endpoint-monitors-en.png) | [لقطة](screens/docs-api-reference-endpoint-monitors-ar.png) |
| `/docs/scout-cli` | Dedicated Scout CLI docs — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-scout-cli-en.png) | [لقطة](screens/docs-scout-cli-ar.png) |
| `/docs/user-guide` | First registered article in a docs section — `` | redirect → /docs/user-guide/quickstart-account-and-trial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-en.png) | [لقطة](screens/docs-user-guide-ar.png) |
| `/docs/user-guide/concept-audience-simulation` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-concept-audience-simulation-en.png) | [لقطة](screens/docs-user-guide-concept-audience-simulation-ar.png) |
| `/docs/user-guide/concept-competitor-monitors` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-concept-competitor-monitors-en.png) | [لقطة](screens/docs-user-guide-concept-competitor-monitors-ar.png) |
| `/docs/user-guide/concept-estimated-vs-real-data` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-concept-estimated-vs-real-data-en.png) | [لقطة](screens/docs-user-guide-concept-estimated-vs-real-data-ar.png) |
| `/docs/user-guide/concept-how-discover-works` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-concept-how-discover-works-en.png) | [لقطة](screens/docs-user-guide-concept-how-discover-works-ar.png) |
| `/docs/user-guide/concept-scoring-system` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-concept-scoring-system-en.png) | [لقطة](screens/docs-user-guide-concept-scoring-system-ar.png) |
| `/docs/user-guide/faq` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-faq-en.png) | [لقطة](screens/docs-user-guide-faq-ar.png) |
| `/docs/user-guide/lead-generation` | Registered static Markdown article — `` | empty / API outcome not provider-verified | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-lead-generation-en.png) | [لقطة](screens/docs-user-guide-lead-generation-ar.png) |
| `/docs/user-guide/quickstart-account-and-trial` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-quickstart-account-and-trial-en.png) | [لقطة](screens/docs-user-guide-quickstart-account-and-trial-ar.png) |
| `/docs/user-guide/quickstart-credits-and-limits` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-quickstart-credits-and-limits-en.png) | [لقطة](screens/docs-user-guide-quickstart-credits-and-limits-ar.png) |
| `/docs/user-guide/quickstart-first-search` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-quickstart-first-search-en.png) | [لقطة](screens/docs-user-guide-quickstart-first-search-ar.png) |
| `/docs/user-guide/quickstart-reading-intelligence` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-quickstart-reading-intelligence-en.png) | [لقطة](screens/docs-user-guide-quickstart-reading-intelligence-ar.png) |
| `/docs/user-guide/quickstart-remix-studio` | Registered static Markdown article — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/docs-user-guide-quickstart-remix-studio-en.png) | [لقطة](screens/docs-user-guide-quickstart-remix-studio-ar.png) |
| `/forgot-password` | Request password reset — `` | partial | POST /auth/forgot-password | [لقطة](screens/forgot-password-en.png) | [لقطة](screens/forgot-password-ar.png) |
| `/guide` | In-app guide — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/guide-en.png) | [لقطة](screens/guide-ar.png) |
| `/intelligence` | Insights, creative/pattern analysis, playbook — `` | partial | /creatives; /patterns; /creatives/{id}/insights; /insights; /playbooks | [لقطة](screens/intelligence-en.png) | [لقطة](screens/intelligence-ar.png) |
| `/legal` | Legal index — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/legal-en.png) | [لقطة](screens/legal-ar.png) |
| `/legal/privacy` | Section-specific legal content — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/legal-privacy-en.png) | [لقطة](screens/legal-privacy-ar.png) |
| `/monitors` | Competitor monitor management, runs and events — `` | empty / API outcome not provider-verified | /monitors/; /monitors/{id}; /monitors/{id}/run; /monitors/events | [لقطة](screens/monitors-en.png) | [لقطة](screens/monitors-ar.png) |
| `/not-a-real-route` | Not-found page after protected route group — `` | empty / API outcome not provider-verified | static / shared auth+chrome calls | [لقطة](screens/not-a-real-route-en.png) | [لقطة](screens/not-a-real-route-ar.png) |
| `/notifications` | Notifications and published updates — `` | empty / API outcome not provider-verified | /notifications/; /notifications/{id}/read; /notifications/read-all; GET /updates | [لقطة](screens/notifications-en.png) | [لقطة](screens/notifications-ar.png) |
| `/performance` | Creative performance, format and time filters — `` | empty / API outcome not provider-verified | /creatives; /monitors* | [لقطة](screens/performance-en.png) | [لقطة](screens/performance-ar.png) |
| `/playbook/audit-not-found` | Shared/public playbook — `` | partial | GET /playbooks/public/{id} | [لقطة](screens/playbook-audit-not-found-en.png) | [لقطة](screens/playbook-audit-not-found-ar.png) |
| `/privacy` | Privacy alias using LegalPage — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/privacy-en.png) | [لقطة](screens/privacy-ar.png) |
| `/reset-password` | Complete reset using token — `` | partial | POST /auth/reset-password | [لقطة](screens/reset-password-en.png) | [لقطة](screens/reset-password-ar.png) |
| `/scout` | Redirect to social Scout — `` | redirect → /scout/social | static / shared auth+chrome calls | [لقطة](screens/scout-en.png) | [لقطة](screens/scout-ar.png) |
| `/scout/lead-generation` | Lead generation jobs and leads — `` | partial | /scout/leadgen/jobs; /scout/leadgen/jobs/{id}; /scout/leadgen/jobs/{id}/leads; /scout/leadgen/recipes; /scout/leadgen/worker/health | [لقطة](screens/scout-lead-generation-en.png) | [لقطة](screens/scout-lead-generation-ar.png) |
| `/scout/maps` | Social or Maps Scout; intended concrete routes /scout/social and /scout/maps — `` | partial | /scout/jobs*; /scout/org-jobs; /scout/latest-job; /scout/settings; /scout/maps/jobs*; /scout/maps/org-jobs; /scout/maps/latest-job | [لقطة](screens/scout-maps-en.png) | [لقطة](screens/scout-maps-ar.png) |
| `/scout/social` | Social or Maps Scout; intended concrete routes /scout/social and /scout/maps — `` | partial | /scout/jobs*; /scout/org-jobs; /scout/latest-job; /scout/settings; /scout/maps/jobs*; /scout/maps/org-jobs; /scout/maps/latest-job | [لقطة](screens/scout-social-en.png) | [لقطة](screens/scout-social-ar.png) |
| `/settings` | Profile and avatar settings — `` | partial | GET/PATCH /account/profile; POST /account/avatar | [لقطة](screens/settings-en.png) | [لقطة](screens/settings-ar.png) |
| `/sign-in` | User sign-in — `` | partial | POST /auth/sign-in; GET /auth/session | [لقطة](screens/sign-in-en.png) | [لقطة](screens/sign-in-ar.png) |
| `/sign-up` | Account registration — `` | partial | POST /auth/sign-up | [لقطة](screens/sign-up-en.png) | [لقطة](screens/sign-up-ar.png) |
| `/support` | Support ticket list, detail, reply — `` | partial | /support/tickets; /support/tickets/{id}; /support/tickets/{id}/reply | [لقطة](screens/support-en.png) | [لقطة](screens/support-ar.png) |
| `/swipe-files` | Saved and custom creative swipe files — `` | empty / API outcome not provider-verified | /creatives/saved; /creatives/custom; media upload | [لقطة](screens/swipe-files-en.png) | [لقطة](screens/swipe-files-ar.png) |
| `/team` | Team members and invitations — `` | partial | /account/team; /account/team/invites; /account/team/members | [لقطة](screens/team-en.png) | [لقطة](screens/team-ar.png) |
| `/team/accept` | Accept team invitation — `` | partial | account team invite acceptance | [لقطة](screens/team-accept-en.png) | [لقطة](screens/team-accept-ar.png) |
| `/terms` | Terms alias using LegalPage — `` | real static content; AR translation partial | static / shared auth+chrome calls | [لقطة](screens/terms-en.png) | [لقطة](screens/terms-ar.png) |
| `/updates` | Published product updates — `` | empty / API outcome not provider-verified | GET /updates | [لقطة](screens/updates-en.png) | [لقطة](screens/updates-ar.png) |

## Tabs / modes / filters / access states

دي الحالات اللي اتفتحت فعليًا. مجرد فتح form/editor من غير Save/Publish مش mutation proof. Detail tabs اللي محتاجة real record/provider output **not verified**؛ ما اتعملتش fake records عشان تتفتح.

| Route | الحالة | Interaction | EN | AR |
|---|---|---|---|---|
| `/admin` | `tab-settled` | networkidle bounded 28s | [لقطة](screens/admin-tab-settled-en.png) | [لقطة](screens/admin-tab-settled-ar.png) |
| `/admin/guide` | `tab-Admin-Center-Operations` | 05Admin Center & Operations (Admins Only)Manage organization limits, daily quotas, feature flags, user roles, and platform health. | [لقطة](screens/admin-guide-tab-Admin-Center-Operations-en.png) | [لقطة](screens/admin-guide-tab-Admin-Center-Operations-ar.png) |
| `/admin/guide` | `tab-Create-Studio-AI-Generation` | 03Create Studio — AI GenerationGenerate photorealistic commercial stills and motion ads with Gemini. | [لقطة](screens/admin-guide-tab-Create-Studio-AI-Generation-en.png) | [لقطة](screens/admin-guide-tab-Create-Studio-AI-Generation-ar.png) |
| `/admin/guide` | `tab-Discover-Competitor-Ad-Extraction` | 01Discover — Competitor Ad ExtractionQuery competitor ad libraries with cost-aware fallback routing and 12-hour deduplication caching. | [لقطة](screens/admin-guide-tab-Discover-Competitor-Ad-Extraction-en.png) | [لقطة](screens/admin-guide-tab-Discover-Competitor-Ad-Extraction-ar.png) |
| `/admin/guide` | `tab-Helix-Architecture-The-4-Loops` | 00Helix Architecture & The 4 LoopsHow Helix unifies competitor ad scraping, AI pattern synthesis, media generation, and performance feedback. | [لقطة](screens/admin-guide-tab-Helix-Architecture-The-4-Loops-en.png) | [لقطة](screens/admin-guide-tab-Helix-Architecture-The-4-Loops-ar.png) |
| `/admin/guide` | `tab-Intelligence-Pattern-Synthesis-Teardowns` | 02Intelligence — Pattern Synthesis & TeardownsExtract hook formulas, emotional triggers, script teardowns, and audience fatigue predictions. | [لقطة](screens/admin-guide-tab-Intelligence-Pattern-Synthesis-Teardowns-en.png) | [لقطة](screens/admin-guide-tab-Intelligence-Pattern-Synthesis-Teardowns-ar.png) |
| `/admin/guide` | `tab-Performance-Longevity-Fatigue-Tracking` | 04Performance — Longevity & Fatigue TrackingBenchmark competitor ad durability, track evergreen survivor rates, and detect creative decay. | [لقطة](screens/admin-guide-tab-Performance-Longevity-Fatigue-Tracking-en.png) | [لقطة](screens/admin-guide-tab-Performance-Longevity-Fatigue-Tracking-ar.png) |
| `/admin/support` | `tab-All-Statuses` | all | [لقطة](screens/admin-support-tab-All-Statuses-en.png) | [لقطة](screens/admin-support-tab-All-Statuses-ar.png) |
| `/admin/support` | `tab-All-Types` | all | [لقطة](screens/admin-support-tab-All-Types-en.png) | [لقطة](screens/admin-support-tab-All-Types-ar.png) |
| `/admin/support` | `tab-Bug-Reports` | bug | [لقطة](screens/admin-support-tab-Bug-Reports-en.png) | [لقطة](screens/admin-support-tab-Bug-Reports-ar.png) |
| `/admin/support` | `tab-Feedback-Ideas` | feedback | [لقطة](screens/admin-support-tab-Feedback-Ideas-en.png) | [لقطة](screens/admin-support-tab-Feedback-Ideas-ar.png) |
| `/admin/support` | `tab-In-Progress` | in_progress | [لقطة](screens/admin-support-tab-In-Progress-en.png) | [لقطة](screens/admin-support-tab-In-Progress-ar.png) |
| `/admin/support` | `tab-Open` | open | [لقطة](screens/admin-support-tab-Open-en.png) | [لقطة](screens/admin-support-tab-Open-ar.png) |
| `/admin/support` | `tab-Resolved` | resolved | [لقطة](screens/admin-support-tab-Resolved-en.png) | [لقطة](screens/admin-support-tab-Resolved-ar.png) |
| `/admin/support` | `tab-Support` | other | [لقطة](screens/admin-support-tab-Support-en.png) | [لقطة](screens/admin-support-tab-Support-ar.png) |
| `/admin/updates` | `tab-editor` | Editor | [لقطة](screens/admin-updates-tab-editor-en.png) | [لقطة](screens/admin-updates-tab-editor-ar.png) |
| `/admin/updates` | `tab-new-editor` | New Update | [لقطة](screens/admin-updates-tab-new-editor-en.png) | [لقطة](screens/admin-updates-tab-new-editor-ar.png) |
| `/admin/updates` | `tab-preview` | Kie.ai Card Preview | [لقطة](screens/admin-updates-tab-preview-en.png) | [لقطة](screens/admin-updates-tab-preview-ar.png) |
| `/admin/usage` | `tab-settled` | networkidle bounded 28s | [لقطة](screens/admin-usage-tab-settled-en.png) | [لقطة](screens/admin-usage-tab-settled-ar.png) |
| `/api-keys` | `tab-spa-navigation` | sidebar-link | [لقطة](screens/api-keys-tab-spa-navigation-en.png) | [لقطة](screens/api-keys-tab-spa-navigation-ar.png) |
| `/billing` | `tab-pending-access` | local pending member; no provider dispatch | [لقطة](screens/billing-tab-pending-access-en.png) | [لقطة](screens/billing-tab-pending-access-ar.png) |
| `/create` | `tab-Image-Creative` | Image Creative | [لقطة](screens/create-tab-Image-Creative-en.png) | [لقطة](screens/create-tab-Image-Creative-ar.png) |
| `/create` | `tab-Image-Creative-Cinematic-Luxury` | Cinematic LuxuryDramatic lighting & editorial scene | [لقطة](screens/create-tab-Image-Creative-Cinematic-Luxury-en.png) | [لقطة](screens/create-tab-Image-Creative-Cinematic-Luxury-ar.png) |
| `/create` | `tab-Image-Creative-Commercial-Ad-Still` | Commercial Ad Still (Default)High-contrast photorealistic ad creative | [لقطة](screens/create-tab-Image-Creative-Commercial-Ad-Still-en.png) | [لقطة](screens/create-tab-Image-Creative-Commercial-Ad-Still-ar.png) |
| `/create` | `tab-Image-Creative-Quick-Concept` | Quick ConceptFast ideation & concept variations | [لقطة](screens/create-tab-Image-Creative-Quick-Concept-en.png) | [لقطة](screens/create-tab-Image-Creative-Quick-Concept-ar.png) |
| `/create` | `tab-Image-Creative-Storyboard-Frame` | Storyboard FrameNarrative scene keyframe | [لقطة](screens/create-tab-Image-Creative-Storyboard-Frame-en.png) | [لقطة](screens/create-tab-Image-Creative-Storyboard-Frame-ar.png) |
| `/create` | `tab-Video-Motion` | Video Motion | [لقطة](screens/create-tab-Video-Motion-en.png) | [لقطة](screens/create-tab-Video-Motion-ar.png) |
| `/create` | `tab-Video-Motion-Before-After` | Before → AfterTransition between two keyframe states | [لقطة](screens/create-tab-Video-Motion-Before-After-en.png) | [لقطة](screens/create-tab-Video-Motion-Before-After-ar.png) |
| `/create` | `tab-Video-Motion-Commercial-Video` | Commercial VideoHigh-fidelity commercial spot | [لقطة](screens/create-tab-Video-Motion-Commercial-Video-en.png) | [لقطة](screens/create-tab-Video-Motion-Commercial-Video-ar.png) |
| `/create` | `tab-Video-Motion-Keyframed-Video` | Keyframed VideoPrecise brand keyframe motion | [لقطة](screens/create-tab-Video-Motion-Keyframed-Video-en.png) | [لقطة](screens/create-tab-Video-Motion-Keyframed-Video-ar.png) |
| `/create` | `tab-Video-Motion-Quick-Motion` | Quick MotionDynamic motion for social ads | [لقطة](screens/create-tab-Video-Motion-Quick-Motion-en.png) | [لقطة](screens/create-tab-Video-Motion-Quick-Motion-ar.png) |
| `/create` | `tab-pending-access` | local pending member; no provider dispatch | [لقطة](screens/create-tab-pending-access-en.png) | [لقطة](screens/create-tab-pending-access-ar.png) |
| `/dashboard` | `tab-settled` | networkidle bounded 28s | [لقطة](screens/dashboard-tab-settled-en.png) | [لقطة](screens/dashboard-tab-settled-ar.png) |
| `/discover` | `tab-drafts-history` | view-only click | [لقطة](screens/discover-tab-drafts-history-en.png) | [لقطة](screens/discover-tab-drafts-history-ar.png) |
| `/discover` | `tab-filters` | view-only click | [لقطة](screens/discover-tab-filters-en.png) | [لقطة](screens/discover-tab-filters-ar.png) |
| `/discover` | `tab-pending-access` | local pending member; no provider dispatch | [لقطة](screens/discover-tab-pending-access-en.png) | [لقطة](screens/discover-tab-pending-access-ar.png) |
| `/guide` | `tab-Admin-Center-Operations` | 05Admin Center & Operations (Admins Only)Manage organization limits, daily quotas, feature flags, user roles, and platform health. | [لقطة](screens/guide-tab-Admin-Center-Operations-en.png) | [لقطة](screens/guide-tab-Admin-Center-Operations-ar.png) |
| `/guide` | `tab-Create-Studio-AI-Generation` | 03Create Studio — AI GenerationGenerate photorealistic commercial stills and motion ads with Gemini. | [لقطة](screens/guide-tab-Create-Studio-AI-Generation-en.png) | [لقطة](screens/guide-tab-Create-Studio-AI-Generation-ar.png) |
| `/guide` | `tab-Discover-Competitor-Ad-Extraction` | 01Discover — Competitor Ad ExtractionQuery competitor ad libraries with cost-aware fallback routing and 12-hour deduplication caching. | [لقطة](screens/guide-tab-Discover-Competitor-Ad-Extraction-en.png) | [لقطة](screens/guide-tab-Discover-Competitor-Ad-Extraction-ar.png) |
| `/guide` | `tab-Helix-Architecture-The-4-Loops` | 00Helix Architecture & The 4 LoopsHow Helix unifies competitor ad scraping, AI pattern synthesis, media generation, and performance feedback. | [لقطة](screens/guide-tab-Helix-Architecture-The-4-Loops-en.png) | [لقطة](screens/guide-tab-Helix-Architecture-The-4-Loops-ar.png) |
| `/guide` | `tab-Intelligence-Pattern-Synthesis-Teardowns` | 02Intelligence — Pattern Synthesis & TeardownsExtract hook formulas, emotional triggers, script teardowns, and audience fatigue predictions. | [لقطة](screens/guide-tab-Intelligence-Pattern-Synthesis-Teardowns-en.png) | [لقطة](screens/guide-tab-Intelligence-Pattern-Synthesis-Teardowns-ar.png) |
| `/guide` | `tab-Performance-Longevity-Fatigue-Tracking` | 04Performance — Longevity & Fatigue TrackingBenchmark competitor ad durability, track evergreen survivor rates, and detect creative decay. | [لقطة](screens/guide-tab-Performance-Longevity-Fatigue-Tracking-en.png) | [لقطة](screens/guide-tab-Performance-Longevity-Fatigue-Tracking-ar.png) |
| `/notifications` | `tab-Alerts` | Alerts | [لقطة](screens/notifications-tab-Alerts-en.png) | [لقطة](screens/notifications-tab-Alerts-ar.png) |
| `/notifications` | `tab-All` | All | [لقطة](screens/notifications-tab-All-en.png) | [لقطة](screens/notifications-tab-All-ar.png) |
| `/notifications` | `tab-Announcements` | Announcements | [لقطة](screens/notifications-tab-Announcements-en.png) | [لقطة](screens/notifications-tab-Announcements-ar.png) |
| `/notifications` | `tab-Unread` | Unread (0) | [لقطة](screens/notifications-tab-Unread-en.png) | [لقطة](screens/notifications-tab-Unread-ar.png) |
| `/scout/maps` | `tab-Active-Workspace` | Active Workspace | [لقطة](screens/scout-maps-tab-Active-Workspace-en.png) | [لقطة](screens/scout-maps-tab-Active-Workspace-ar.png) |
| `/scout/maps` | `tab-Org-Maps-Jobs` | Org Maps Jobs (0) | [لقطة](screens/scout-maps-tab-Org-Maps-Jobs-en.png) | [لقطة](screens/scout-maps-tab-Org-Maps-Jobs-ar.png) |
| `/scout/maps` | `tab-Org-Social-Jobs` | Org Social Jobs (0) | [لقطة](screens/scout-maps-tab-Org-Social-Jobs-en.png) | [لقطة](screens/scout-maps-tab-Org-Social-Jobs-ar.png) |
| `/scout/social` | `tab-Active-Workspace` | Active Workspace | [لقطة](screens/scout-social-tab-Active-Workspace-en.png) | [لقطة](screens/scout-social-tab-Active-Workspace-ar.png) |
| `/scout/social` | `tab-Org-Maps-Jobs` | Org Maps Jobs (0) | [لقطة](screens/scout-social-tab-Org-Maps-Jobs-en.png) | [لقطة](screens/scout-social-tab-Org-Maps-Jobs-ar.png) |
| `/scout/social` | `tab-Org-Social-Jobs` | Org Social Jobs (0) | [لقطة](screens/scout-social-tab-Org-Social-Jobs-en.png) | [لقطة](screens/scout-social-tab-Org-Social-Jobs-ar.png) |

## توقيتات الـpreview وحدودها

مافيش production قياس أو load test. `loadMs` في أعلى capture record يشمل CLI/انتظار/فحص DOM؛ مايتقالش عليه LCP أو page-load pure. الأرقام الجاية من browser Performance Navigation Timing فقط، على جهاز shared sandbox مع empty DB وdevelopment Vite، ومفيهاش ضمان API/provider completion.
- عدد navigation timing samples الصالحة: **172** (فيهم repeated page loads؛ مش unique users).
- `responseMs`: min **6.0ms**، median **22.4ms**، max **609.0ms**. ده descriptive للعينات دي بس، مش p95/SLO.
- `domMs`: min **214.6ms**، median **829.5ms**، max **1556.5ms**. ده descriptive للعينات دي بس، مش p95/SLO.
- `loadMs`: min **166.9ms**، median **861.6ms**، max **3006.0ms**. ده descriptive للعينات دي بس، مش p95/SLO.

## Browser findings مؤكدة

- `/api-keys`: direct GET بيتحوّل للbackend بسبب dev proxy `/api` prefix؛ JSON404. Sidebar SPA entry فتح API-keys UI؛ production direct-load **not verified**.
- pending account على Create بيشوف trial-ended/select-plan language رغم access pending. billing/access متداخلين.
- `lang/dir` اتبدلوا EN→AR/RTL؛ docs/auth/admin/Create وغيرهم لسه بيعرضوا English. Screenshots دليل partial localization مش compliance.
- dashboard/admin/usage عندهم initial skeletons ثم settled captures منفصلة؛ ما اتوصّفوش permanent hang من snapshot مبكر.
- provider-dependent populated details، generation، إرسال emails/invites، published updates وreal lead/job details: **not verified**.
