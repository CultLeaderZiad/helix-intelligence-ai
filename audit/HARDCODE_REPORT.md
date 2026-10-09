# Hardcode & Mock Usage Audit Report

## Phase 1 Findings

This document tracks all hardcoded strings, mock data usage, and dummy states found across the codebase that need to be replaced with real database/API calls or configuration.

### Backend (`USE_MOCKS` pattern)
The backend architecture uses a configuration toggle (`settings.USE_MOCKS`) which bypasses the database and returns hardcoded dictionaries. Found in:
- `backend/app/services/media_service.py`
- `backend/app/services/discover_service.py`
- `backend/app/services/dashboard_service.py`
- `backend/app/services/creative_service.py`
- `backend/app/services/billing_service.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/analysis_service.py`
- `backend/app/services/admin_service.py`

### Frontend Hardcoded Data
- `src/features/marketing/PricingSection.jsx` (Lines 12-60): Hardcoded `TIERS` constant containing pricing data, features, and plans.
- `src/data/brands.js`
- `src/data/creatives.js`
- `src/data/insights.js`
- `src/data/jobs.js`
- `src/data/patterns.js`
*(Update: Verified that some UI components directly import these files instead of using API responses)*
- `src/features/scout-leadgen/RecipeLibrary.jsx`: Imports JSON files directly from `app/data/leadgen_recipes` (comments indicate this, will need to check).
- `src/features/discover/JobProgress.jsx`: Imports `DISCOVERY_STAGES` directly from `@/data/jobs`.
- `src/features/discover/ResultsTable.jsx`: Imports `brandsById` directly from `@/data/brands`.

### Hardcoded Lists and Options in Frontend
- `src/features/scout-leadgen/ScoutLeadGenSubNav.jsx`: `TABS`
- `src/features/scout-leadgen/LeadDetail.jsx`: `TABS`
- `src/features/scout-leadgen/EnginePicker.jsx`: `ENGINES`, `MODES`
- `src/features/scout/TargetCategoryField.jsx`: `CATEGORY_PRESETS`
- `src/features/scout/PlatformPicker.jsx`: `AVAILABLE_PLATFORMS`
- `src/features/scout/MapsQueryForm.jsx`: `SUGGESTED_NICHES`, `SUGGESTED_CITIES`
- `src/features/marketing/Hero.jsx`: `PRODUCT_STEPS`, `COMPETITOR_SCENARIOS`
- `src/features/docs/docsData.js`: `DOCS_REGISTRY`
- `src/features/discover/FilterRail.jsx`: `SCORE_OPTIONS`, `DAYS_OPTIONS`
- `src/features/auth/PasswordStrength.jsx`: `TIERS`

### VITE_DATA_SOURCE Mock Logic
- `src/services/config.js` sets `rawDataSource = (env.VITE_DATA_SOURCE ?? "api")`. If it isn't "api", it falls back to mock logic, returning dummy responses from `src/services/mock/` files.
