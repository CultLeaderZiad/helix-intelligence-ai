# API Reference: Discover Endpoints

The Discover API allows you to trigger background ad library extraction jobs, poll job progress, and retrieve scored creative records.

---

## 1. Trigger a Discovery Search Job

Enqueues an asynchronous ad-library extraction pipeline for a given brand name, product query, or competitor keyword.

```http
POST /api/discovery/jobs
Content-Type: application/json
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Request Body (`SearchParams`)

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `query` | `string` | **Yes** | — | Brand name, competitor query, or product search term. |
| `filters` | `object` | No | `{}` | Optional dictionary of filters (e.g. `{"platform": "meta", "format": "video"}`). |
| `sort` | `string` | No | `"composite_desc"` | Sorting order: `composite_desc`, `durability_desc`, or `date_desc`. |
| `page` | `integer` | No | `1` | Results page offset. |
| `page_size` | `integer` | No | `20` | Results per page (max 50). |
| `query_language` | `string` | No | `"en"` | Language code (`"en"`, `"ar"`, `"es"`, `"zh"`, `"nl"`). |

#### Example Request

```json
{
  "query": "Athletic Greens",
  "filters": {
    "platform": "meta",
    "format": "video"
  },
  "sort": "composite_desc",
  "page": 1,
  "page_size": 20,
  "query_language": "en"
}
```

### Response Body (`Job`)

Returns HTTP `200 OK` with the initial job status:

```json
{
  "job_id": "job_01j7b9k2x4p0m",
  "status": "in_progress",
  "progress": 0.25,
  "stage": "targeting_ad_libraries",
  "stage_label": "Targeting verified ad libraries",
  "stage_index": 1,
  "stages_total": 4,
  "records_found": 0,
  "elapsed_ms": 420,
  "created_at": "2026-09-14T12:00:00.000Z",
  "completed_at": null,
  "error": null,
  "failure_kind": null,
  "entity_profile": {
    "brand_name": "Athletic Greens",
    "verified": true,
    "primary_domain": "drinkag1.com"
  }
}
```

---

## 2. Poll Job Status

Check the live progress, execution stage, and record counts of an enqueued job.

```http
GET /api/discovery/jobs/{job_id}
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response Body (`Job` - Completed State)

```json
{
  "job_id": "job_01j7b9k2x4p0m",
  "status": "ready",
  "progress": 1.0,
  "stage": "completed",
  "stage_label": "Scrape complete. All scores calculated.",
  "stage_index": 4,
  "stages_total": 4,
  "records_found": 36,
  "elapsed_ms": 3840,
  "created_at": "2026-09-14T12:00:00.000Z",
  "completed_at": "2026-09-14T12:00:03.840Z",
  "error": null,
  "failure_kind": null,
  "entity_profile": {
    "brand_name": "Athletic Greens",
    "primary_domain": "drinkag1.com"
  }
}
```

---

## 3. Retrieve Job Creative Results

Retrieve the paginated creative records extracted by a completed job.

```http
GET /api/discovery/jobs/{job_id}/results?page=1&page_size=20
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response Body (`Paginated[Creative]`)

```json
{
  "items": [
    {
      "id": "crt_01j7b9k2x8r4e",
      "brand_id": "brd_ag1",
      "brand_name": "Athletic Greens",
      "platform": "meta",
      "format": "video",
      "source_type": "ad",
      "headline": "Replace your morning pill clutter with 1 simple scoop.",
      "body": "75 vitamins, minerals, and whole-food sourced nutrients. Backed by science, trusted by world-class athletes. Order now and get a free 1-year supply of Vitamin D3+K2.",
      "cta": "Shop Now",
      "landing_domain": "drinkag1.com",
      "media_url": "https://storage.helix.io/creatives/ag1_morning_scoop.mp4",
      "thumbnail_url": "https://storage.helix.io/creatives/ag1_morning_thumb.jpg",
      "thumbnail_ratio": "9:16",
      "duration_seconds": 28,
      "first_seen": "2026-08-01T09:00:00Z",
      "last_seen": "2026-09-14T10:00:00Z",
      "days_active": 44,
      "variant_count": 6,
      "scores": {
        "hook": 91.5,
        "clarity": 88.0,
        "retention": 84.2,
        "composite": 88.4
      },
      "metrics": {
        "impressions_est": 450000,
        "is_impression_estimate": true,
        "spend_band": "$10k-$50k",
        "engagement_rate": 0.048,
        "ctr_est": 0.024
      },
      "pattern_ids": ["pat_morning_routine_demo", "pat_founder_authority"]
    }
  ],
  "total": 36,
  "page": 1,
  "page_size": 20,
  "pages": 2
}
```

👉 [Creatives Endpoints](/docs/api-reference/endpoint-creatives)
