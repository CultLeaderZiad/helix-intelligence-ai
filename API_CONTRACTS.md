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

### Insufficient Plan Credits (HTTP 402)
```json
{
  "code": "insufficient_credits",
  "message": "Not enough credits for this action (0.0 available, 3.0 required). Upgrade or wait for trial reset.",
  "credit_balance": 0.0,
  "required": 3.0,
  "plan_name": "7-Day Free Trial"
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
  "parameters": { ... }
}
```

### Get Media Job Status
`GET /api/media/jobs/{job_id}`

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

---

## 4. Provider & Model Architecture

- **Image Provider**: `GeminiProvider` using Google Gemini API (`gemini-3.1-flash-image`).
- **Vision & Analysis**: `GeminiProvider` multimodal vision analysis.
- **Provider Quota vs Application Quota**: Google provider free-tier/model availability is separate from application-level trial limits. Rate limit responses (HTTP 429) do not consume user daily image allowance.
