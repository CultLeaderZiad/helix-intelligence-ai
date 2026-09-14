# API Reference: Credit Costs & Rate Limits

Programmatic API calls consume credits from your organization's pooled ledger. Costs are metered per endpoint according to real compute requirements.

---

## 1. Official Credit Schedule

The values below match the live `CREDIT_COSTS` dictionary in `backend/app/services/billing_service.py` exactly:

| Billing Key | Action / Endpoint | Cost | Description |
| :--- | :--- | :--- | :--- |
| `discover_job` | `POST /api/discovery/jobs` | `1.0` credit | Dispatches public ad library scrape and scores initial results. |
| `discover_deep_fallback` | Extended Search Pipeline | `2.0` credits | Engaged when an entity has sparse recent ads, invoking multi-provider fallbacks. |
| `ai_insight` | `POST /api/creatives/{id}/generate-insights` | `0.5` credit | Generates deep hook transcript analysis and angle taxonomy. |
| `pattern_pack` | Creative Clustering Engine | `0.5` credit | Extracts high-leverage creative patterns across multiple ads. |
| `ai_chat` | Interactive Creative Assistant | `0.25` credit | LLM query answering questions on creative performance or trends. |
| `audience_simulation` | `POST /api/simulation/run` | `1.0` credit | Multi-persona qualitative rehearsal across target buyer segments. |
| `create_image` | `POST /api/media/jobs` (image) | `2.0` credits | Generates an AI visual asset via Higgsfield AI pipelines. |
| `create_video` | `POST /api/media/jobs` (video) | `5.0` credits | Renders an AI motion video variant. |

---

## 2. Preventing Documentation Drift

> [!IMPORTANT]
> **Source of Truth Notice**:
> The backend server enforces billing strictly from `CREDIT_COSTS` defined in `backend/app/services/billing_service.py`.
> To prevent documentation drift, CI checks and automated schema tests assert that the documented credit table above mirrors the Python constants file.
> You can also query the live active plan limits programmatically via `GET /api/account/trial-status` or `GET /api/account/billing`.

---

## 3. Rate Limits & Quota Mechanics

1. **Daily Reset**:
   - All daily limits reset automatically at **00:00:00 UTC**.
   - Your account's next reset time is returned in the `daily_credits_resets_at_utc` field of `GET /api/account/trial-status`.
2. **Atomic Deduction**:
   - Credits are reserved atomically when a job is enqueued.
3. **Automatic Refund on Failure**:
   - If an extraction or generation job fails (for example, due to an ad network timeout or provider restart), the backend triggers `billing_service.refund()`. Your credits are instantly returned.
4. **Concurrent Requests**:
   - Trial accounts are limited to 2 concurrent background jobs.
   - Pro and Enterprise accounts support up to 20 concurrent jobs.

👉 [Discover Endpoints](/docs/api-reference/endpoint-discover)
