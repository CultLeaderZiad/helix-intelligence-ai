# Render environment for W8, and secret rotation (names only, no values)

## A. What the W8 backend needs on Render (`srv-da3ocem7bikc73bfi4fg`)

Compared against Render's environment export of 2026-11-08, names only.

| Name | W8 needs | Render today | Action |
|---|---|---|---|
| `ENVIRONMENT` | `production` | missing | add |
| `DATABASE_URL` | `helix_api_login` on the pooled host of branch `br-gentle-star-axcrbk22` | owner role | switch at deploy (runbook step 7); keep the owner URL for rollback |
| `PUBLIC_APP_BASE_URL`, `APP_BASE_URL` | public https (Vercel URL) | missing | add |
| `PUBLIC_API_BASE_URL` | public https API URL | present | keep |
| `BACKEND_CORS_ORIGINS` | https Vercel origin(s) only | present, includes `localhost` | edit |
| `SECRET_KEY` | ≥ 32 chars | present | rotate (signs sessions; rotating signs everyone out) |
| `CREDENTIAL_ENCRYPTION_KEY` | set, different from `SECRET_KEY` | missing | add |
| `RESEND_API_KEY`, `RESEND_FROM` | set (production refuses to start without them) | missing | add |
| `EMBEDDED_WORKER_ENABLED` | `true` (free plan has no worker service) | missing | add |
| `HELIX_DISPATCH_INLINE` | `false` or unset | unset | ok |
| `METAPI_API_KEY` | set | present | rotate |
| `METAPI_MONTHLY_RECORD_BUDGET` | the remaining records this period | missing (default 3000) | add |
| `DISCOVER_*` caps | as decided (defaults: 6 calls/day, 3 searches/workspace) | missing (defaults) | optional |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | optional AI providers | present | rotate |
| `ADYNTEL_API_KEY`, `ADYNTEL_EMAIL`, `META_ACCESS_TOKEN`, `APIFY_API_TOKEN`, `SCRAPEGRAPH_API_KEY`, `BRIGHTDATA_API_KEY` | optional providers | present | rotate, or remove if unused |
| `GROQ_MODEL`, `GEMINI_TEXT_MODEL` | have code defaults | missing | ok |
| `HELIX_PLATFORM_ADMIN_EMAILS` | used only when migrating, on your machine | n/a | not on Render |

**Present on Render but not read by the W8 backend** (candidates to delete after rotating):
- `AIHUBMIX_API_KEY`
- `DATABASE_URL_UNPOOLED`
- `HF_API_KEY_ID`, `HF_API_KEY_SECRET`
- `HIGGSFIELD_BASE_URL`
- `NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN`
- `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`, `NEON_BRANCH`
- `TOKENHARBOR_API_KEY`
- `USE_MOCKS`
- `VITE_DATA_SOURCE` (a frontend setting; it belongs on Vercel, not Render)

Check: Export → Download .env, then `python backend/scripts/check_release_env.py --env-file <file>`. Every line must be OK.

## B. Rotation checklist

The env file shared on 2026-11-08 exposed every value below in a chat transcript. Rotate each one, update **Render** (and any local `.env.local`), then confirm the old value no longer works. Never paste a new value into chat.

| # | Secret | Where to rotate | When | Notes |
|---|---|---|---|---|
| 1 | Neon owner password (`neondb_owner`, used by `DATABASE_URL` / `_UNPOOLED`) | Neon console → Roles → `neondb_owner` → Reset password | **At cutover**, right after migrating | Rotating breaks the running old API until Render's `DATABASE_URL` changes, so do it in the same window. Keep the new owner URL only for migrations and rollback. |
| 2 | `SECRET_KEY` | Generate locally (≥ 48 random chars) | At cutover | Invalidates all sessions; users sign in again. |
| 3 | `METAPI_API_KEY` | Metapi dashboard → API keys → revoke and create | Before cutover | Then set `METAPI_MONTHLY_RECORD_BUDGET`. |
| 4 | `GROQ_API_KEY` | console.groq.com → API Keys | Before cutover | |
| 5 | `GEMINI_API_KEY` | Google AI Studio → API keys | Before cutover | |
| 6 | `RESEND_API_KEY` (new) | resend.com → API Keys, sending-only scope | Before cutover | Verify the sender domain for `RESEND_FROM`. |
| 7 | `META_ACCESS_TOKEN` | Meta for Developers → app → regenerate / invalidate | Before cutover | Long-lived user token; invalidate the old one. |
| 8 | `OPENROUTER_API_KEY` | openrouter.ai → Keys | Before cutover | |
| 9 | `APIFY_API_TOKEN` | Apify console → Integrations → API tokens | Before cutover | |
| 10 | `ADYNTEL_API_KEY` | Adyntel dashboard | Before cutover | |
| 11 | `SCRAPEGRAPH_API_KEY` | ScrapeGraph dashboard | Before cutover | |
| 12 | `BRIGHTDATA_API_KEY` | Bright Data → API tokens | Before cutover | |
| 13 | `NEON_AI_GATEWAY_TOKEN` | Neon console | Before cutover | Unused by W8: revoke, delete from Render. |
| 14 | `HF_API_KEY_ID` / `HF_API_KEY_SECRET` | Provider dashboard | Before cutover | Unused by W8: revoke, delete. |
| 15 | `AIHUBMIX_API_KEY`, `TOKENHARBOR_API_KEY` | Provider dashboards | Before cutover | Unused by W8: revoke, delete. |
| 16 | New `helix_api_login` password | Generated at cutover (runbook step 4) | At cutover | Only in a password manager and in Render's `DATABASE_URL`. |
| 17 | New `CREDENTIAL_ENCRYPTION_KEY` | Generate locally | Before cutover | Different from `SECRET_KEY`. |
