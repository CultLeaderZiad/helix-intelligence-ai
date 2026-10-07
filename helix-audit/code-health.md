# Appendix 3 — Code health and coverage

All 525 tracked files were inventoried and hashed. Text files received static scanning; semantic traces and focused tests are recorded separately. This ledger does not claim every possible runtime behavior was exercised. Binary images/fonts were inventoried, not treated as executable source. No repository source was changed.

## Every tracked text file over 500 lines

| File | Lines |
|---|---|
| [backend/metapi_dict_sample.json:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/metapi_dict_sample.json:1) | 4191 |
| [backend/scripts/raw_metapi_gymshark.json:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/scripts/raw_metapi_gymshark.json:1) | 3327 |
| [backend/scripts/raw_metapi_shopify.json:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/scripts/raw_metapi_shopify.json:1) | 3087 |
| [pnpm-lock.yaml:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/pnpm-lock.yaml:1) | 1898 |
| [src/pages/IntelligencePage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/IntelligencePage.jsx:1) | 1098 |
| [backend/app/services/monitor_service.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/monitor_service.py:1) | 833 |
| [src/pages/CreatePage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/CreatePage.jsx:1) | 795 |
| [backend/app/services/leadgen_pipeline.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/leadgen_pipeline.py:1) | 788 |
| [backend/app/services/creative_service.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/creative_service.py:1) | 755 |
| [backend/app/services/billing_service.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/billing_service.py:1) | 753 |
| [backend/app/services/admin_service.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/admin_service.py:1) | 741 |
| [src/pages/admin/UpdatesPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/admin/UpdatesPage.jsx:1) | 713 |
| [backend/app/api/routers/scout.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/api/routers/scout.py:1) | 699 |
| [src/data/creatives.js:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/data/creatives.js:1) | 686 |
| [backend/app/services/discover_service.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/discover_service.py:1) | 653 |
| [src/features/marketing/LoopsSection.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/features/marketing/LoopsSection.jsx:1) | 647 |
| [src/pages/DashboardPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/DashboardPage.jsx:1) | 641 |
| [src/pages/ScoutPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/ScoutPage.jsx:1) | 616 |
| [backend/app/api/routers/leadgen.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/api/routers/leadgen.py:1) | 600 |
| [src/pages/PerformancePage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/PerformancePage.jsx:1) | 600 |
| [src/pages/ApiKeysPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/ApiKeysPage.jsx:1) | 578 |
| [src/pages/DiscoverPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/DiscoverPage.jsx:1) | 532 |
| [src/features/docs/MarkdownRenderer.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/features/docs/MarkdownRenderer.jsx:1) | 531 |
| [src/features/marketing/Hero.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/features/marketing/Hero.jsx:1) | 515 |
| [src/features/docs/DocsLayout.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/features/docs/DocsLayout.jsx:1) | 513 |
| [src/features/discover/EntityDossierCard.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/features/discover/EntityDossierCard.jsx:1) | 511 |
| [backend/app/services/entity_intelligence.py:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/entity_intelligence.py:1) | 504 |
| [src/pages/admin/SubscriptionsPlansPage.jsx:1](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/admin/SubscriptionsPlansPage.jsx:1) | 504 |

## TODO / FIXME / HACK / XXX markers

These are inventory entries, not automatically production findings. Binary assets excluded.
No exact-word TODO/FIXME/HACK/XXX markers in tracked UTF-8 text.

## Concrete dead/duplicated paths

- [backend/app/services/storage_service.py:183](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/storage_service.py:183) `store_media_from_url` has no current caller; its error fallback must not be relied on as durable persistence.
- [backend/app/core/config.py:196](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/core/config.py:196) SCRAPLING_MAX_CONCURRENCY has no consumer; the worker loop runs one job at a time. Setting it to 4 does not create concurrency.
- Insight fallback text is duplicated in [backend/app/services/ai/base.py:60](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/ai/base.py:60), [backend/app/services/analysis_service.py:121](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/services/analysis_service.py:121) and [src/pages/IntelligencePage.jsx:346](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/src/pages/IntelligencePage.jsx:346).
- Duplicate health registrations in [backend/app/main.py:255](/home/vercel-sandbox/workspace/repos/github.com/cultleaderziad/helix-intelligence-ai/backend/app/main.py:255) overlap the health router; route-matrix.md retains duplicates.

See frontend-state-inventory.json for every page and detected data-fetching component/hook, with static loading/empty/error signals. Signal presence is not evidence of correct rendering; defects with concrete paths are in the findings. Visual Arabic/RTL, screen-reader and contrast verification remain outstanding.
