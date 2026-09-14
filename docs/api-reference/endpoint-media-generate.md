# API Reference: Media Generation Endpoints

The Media Generation API interfaces directly with Helix's media rendering pipeline (powered by Higgsfield AI) to generate advertising images and motion video variants.

---

## 1. Create Media Generation Job

Enqueues an asynchronous generation job for an ad image or motion video asset.

```http
POST /api/media/jobs
Content-Type: application/json
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Request Body (`MediaGenerationRequest`)

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | `string` | **Yes** | — | Detailed creative prompt describing the visual, subject, lighting, and style. |
| `provider` | `string` | No | `"higgsfield"` | Target generation engine. |
| `mode` | `string` | No | `"premium_ad"` | Generation profile: `"premium_ad"`, `"fast_preview"`, or `"cinematic_video"`. |
| `parameters` | `object` | No | `{}` | Optional generation parameters (e.g. `aspect_ratio`, `motion_strength`, `negative_prompt`). |

> [!NOTE]
> Image generation deducts **2.0 credits**. Video motion generation deducts **5.0 credits**.

#### Example Request

```json
{
  "prompt": "Cinematic product hero shot of a minimalist amber glass serum bottle on dark granite stone, soft water droplets, sharp morning sidelight, premium luxury cosmetic commercial aesthetic",
  "provider": "higgsfield",
  "mode": "premium_ad",
  "parameters": {
    "aspect_ratio": "9:16",
    "quality_steps": 30
  }
}
```

### Response Body (`MediaGenerationJobResponse`)

```json
{
  "id": "med_01j7b9k2x4p0m",
  "job_id": "med_01j7b9k2x4p0m",
  "status": "pending",
  "prompt": "Cinematic product hero shot of a minimalist amber glass serum bottle on dark granite stone...",
  "provider": "higgsfield",
  "provider_job_id": "hg_req_7829104",
  "created_at": "2026-09-14T12:20:00.000Z",
  "updated_at": "2026-09-14T12:20:00.000Z",
  "parameters": {
    "aspect_ratio": "9:16",
    "quality_steps": 30
  },
  "result_url": null,
  "error_message": null,
  "failure_kind": null
}
```

---

## 2. Poll Media Job Status

Poll the state of a media rendering job until completion.

```http
GET /api/media/jobs/{job_id}
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Completed Response (`MediaGenerationJobResponse`)

```json
{
  "id": "med_01j7b9k2x4p0m",
  "job_id": "med_01j7b9k2x4p0m",
  "status": "completed",
  "prompt": "Cinematic product hero shot of a minimalist amber glass serum bottle...",
  "provider": "higgsfield",
  "provider_job_id": "hg_req_7829104",
  "created_at": "2026-09-14T12:20:00.000Z",
  "updated_at": "2026-09-14T12:20:12.450Z",
  "parameters": {
    "aspect_ratio": "9:16"
  },
  "result_url": "https://storage.helix.io/renders/med_01j7b9k2x4p0m.png",
  "error_message": null,
  "failure_kind": null
}
```

---

## 3. List Available Media Providers & Capabilities

Inspect active backend rendering providers and current generation models.

```http
GET /api/media/providers
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response

```json
[
  {
    "id": "higgsfield",
    "name": "Higgsfield AI",
    "capabilities": [
      "IMAGE_FAST",
      "IMAGE_PREMIUM",
      "IMAGE_CINEMATIC",
      "VIDEO_FAST",
      "VIDEO_STANDARD",
      "VIDEO_FIRST_LAST_FAST",
      "VIDEO_FIRST_LAST_STANDARD"
    ],
    "status": "active"
  }
]
```

👉 [Monitors Endpoints](/docs/api-reference/endpoint-monitors)
