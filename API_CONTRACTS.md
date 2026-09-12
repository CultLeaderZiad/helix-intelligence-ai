# HELIX Intelligence — API Contracts & Entitlements

## 1. 7-Day Free Trial & Image Generation Entitlements

HELIX offers a 7-day full access free trial with daily image creation allowances:

- **Trial Duration**: 7 days from signup (`trial_started_at` to `trial_expires_at`).
- **Trial Daily Image Limit**: 5 images per UTC day (resets daily at 00:00 UTC).
- **Trial Total Image Cap**: 25 total images across the trial window.
- **Paid Plans Allowance**: 50+ images per day.
- **Admin Users**: Unlimited bypass across all media generation and features.
- **Video Generation on Trial**: Strictly disabled during trial; available exclusively on paid plans.

---

## 2. Server-Side Entitlement Error Contract (HTTP 402 / 429)

All generation and entitlement gatekeeper failures return machine-readable JSON envelopes with HTTP 402 / 429 status codes:

### Daily Image Limit Exceeded (HTTP 402)
```json
{
  "code": "daily_limit",
  "message": "You've reached today's limit of 5 images. Your quota resets at 00:00 UTC.",
  "images_used_today": 5,
  "images_daily_limit": 5,
  "images_remaining_today": 0,
  "trial_days_remaining": 4
}
```

### Total Trial Cap Exceeded (HTTP 402)
```json
{
  "code": "trial_total_limit",
  "message": "You've reached your total trial allowance of 25 images. Upgrade to continue creating.",
  "images_used_today": 5,
  "images_daily_limit": 5,
  "images_remaining_today": 0,
  "trial_days_remaining": 3
}
```

### Trial Expired (HTTP 402)
```json
{
  "code": "trial_expired",
  "message": "Your 7-day free trial has ended. Select a plan to continue creating AI ads.",
  "images_used_today": 5,
  "images_daily_limit": 5,
  "images_remaining_today": 0,
  "trial_days_remaining": 0
}
```

### Video Generation Attempt on Trial (HTTP 402)
```json
{
  "code": "video_not_allowed",
  "message": "Video generation is available exclusively on paid plans. Upgrade to unlock AI video creation.",
  "trial_days_remaining": 5
}
```

### BYOK Key Error / Quota Exhausted (No Silent Fallback) (HTTP 400 / 502)
```json
{
  "code": "byok_provider_unavailable",
  "message": "Your connected Gemini account is unavailable. Check your API key or Google quota."
}
```

---

## 3. Media Creation Endpoints

### Create Media Job
`POST /api/media/jobs` (or `/api/v1/media/jobs`)

**Headers:**
- `Authorization: Bearer <jwt_token>`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "prompt": "Commercial studio shot of organic energy drink on slate rock...",
  "provider": "gemini",
  "mode": "premium_ad",
  "parameters": {
    "aspect_ratio": "1:1",
    "kind": "image",
    "source_creative_id": "c_123",
    "reference_images": ["https://example.com/ref.jpg"]
  }
}
```

**Response (200 OK):**
```json
{
  "id": "job_uuid",
  "job_id": "job_uuid",
  "status": "pending",
  "prompt": "Commercial studio shot...",
  "provider": "gemini",
  "created_at": "2026-08-31T04:00:00Z",
  "updated_at": "2026-08-31T04:00:00Z",
  "parameters": { "credential_mode": "managed", "model": "gemini-3.1-flash-image" }
}
```

### Get Media Job Status
`GET /api/media/jobs/{job_id}`

Scoped to the caller: the row must belong to this user or to their workspace.
A job id is not a capability, so another account's id answers `404` (not `403`)
and the same rule applies to cancel.

**Response (200 OK):**
```json
{
  "id": "job_uuid",
  "job_id": "job_uuid",
  "status": "completed",
  "result_url": "/uploads/job_uuid_abc123.png",
  "error_message": null
}
```

**Response (404 Not Found):** `{"detail": "Job not found"}` — also the answer
for a job that exists but belongs to somebody else.

### Cancel Media Job
`POST /api/media/jobs/{job_id}/cancel`

Cancels a job that has not produced a result yet (`pending`, `queued`,
`running`, `in_progress`, `processing`). The provider task re-reads the status
before it dispatches and again before it records usage, so a cancelled attempt
is never billed. A generation already in flight at the provider cannot be
recalled over our transport; the message says so instead of promising an abort.

**Response (200 OK):**
```json
{
  "success": true,
  "job_id": "job_uuid",
  "status": "canceled",
  "message": "Job canceled. Credits for this attempt were not charged."
}
```

**Response (409 Conflict)** — already settled, nothing to cancel:
```json
{
  "detail": {
    "code": "job_not_cancellable",
    "message": "This job is already completed, so there is nothing to cancel.",
    "job_id": "job_uuid",
    "status": "completed"
  }
}
```

**Response (404 Not Found)** — unknown id, or a job belonging to another
account. A cancelled job that the provider finishes later stays `canceled` and
its result is discarded.

---

## 4. Workspace BYOK Endpoints (Google Gemini)

### Get Workspace Providers
`GET /api/workspaces/providers`

**Response (200 OK):**
```json
{
  "workspace_id": "org_uuid",
  "workspace_name": "Acme Agency's Workspace",
  "providers": [
    {
      "provider": "google_gemini",
      "name": "Google Gemini",
      "supported_models": ["gemini-3.1-flash-image", "gemini-flash-latest"],
      "default_image_model": "gemini-3.1-flash-image",
      "credential_mode": "byok",
      "is_byok_configured": true,
      "status": "connected",
      "masked_key": "••••••••9988",
      "last_tested_at": "2026-08-31T04:20:00Z"
    }
  ]
}
```

### Connect / Encrypt Gemini BYOK Key
`POST /api/workspaces/provider-credentials/google-gemini`

**Request Body:**
```json
{
  "api_key": "AIzaSy...",
  "credential_mode": "byok"
}
```

**Response (200 OK):**
```json
{
  "status": "connected",
  "provider": "google_gemini",
  "credential_mode": "byok",
  "masked_key": "••••••••1234",
  "message": "Gemini API key encrypted and connected successfully"
}
```

### Remove BYOK Key
`DELETE /api/workspaces/provider-credentials/google-gemini`

**Response (200 OK):**
```json
{
  "status": "deleted",
  "provider": "google_gemini",
  "credential_mode": "managed",
  "message": "Gemini BYOK key removed. Workspace restored to HELIX Managed provider."
}
```

---

## 5. Security & Provider Resolution Guarantees

1. **Server-Side Encryption**: All customer BYOK keys are encrypted at rest using AES / Fernet ciphers derived from the server's `SECRET_KEY`.
2. **Never Exposed**: Plaintext keys are NEVER returned in API responses, logs, or stored in frontend state. Responses only display masked suffixes (`••••••••abcd`).
3. **Trial Isolation**: Trial users always use HELIX Managed Gemini.
4. **No Silent Fallback**: If a paid workspace configures BYOK and the customer's Google project fails or runs out of quota, HELIX returns an explicit notice and never silently bills HELIX infrastructure.
