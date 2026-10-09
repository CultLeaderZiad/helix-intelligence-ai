# Build & Test Audit Report

## Phase 2 Findings

This document tracks the results of verifying that every page, route, job, and build runs with zero errors and zero warnings that matter.

### Frontend Build
- **Command:** `npm run build`
- **Result:** Success (Exit code 0).
- **Warnings:** Only a chunk size warning (`index-CEi37o6P.js` is 579.65 kB). No lint or critical build errors.

### Backend Tests
- **Command:** `pytest tests/`
- **Result:** Success (Exit code 0, 62 passed).
- **Warnings:** 
  - `MovedIn20Warning` in `app/db/base.py:3` (`declarative_base()`)
  - `PydanticDeprecatedSince20` in `app/schemas/app_update.py:34` and `app/schemas/media.py:11`
  - `RuntimeWarning` in `test_f25_reconciliation_sweeper_handles_all_job_types`: coroutine `AsyncMockMixin._execute_mock_call` was never awaited.
  *(These are minor deprecation/mock warnings, no application-level logic warnings were found)*
