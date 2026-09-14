# API Reference: Creatives Endpoints

The Creatives API lets you query indexed competitor ads, access detailed multimodal analysis, and manage swipe file collections.

---

## 1. List Creatives

Query active creatives filtered by scrape job, brand identifier, or pagination parameters.

```http
GET /api/creatives?brand_id=brd_ag1&page=1&page_size=20
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `job_id` | `string` | No | Filter creatives belonging to a specific discovery scrape job. |
| `brand_id` | `string` | No | Filter by unique brand identifier. |
| `page` | `integer` | No | Page number (default: `1`). |
| `page_size` | `integer` | No | Number of records per page (default: `20`, max: `100`). |

### Response (`Paginated[Creative]`)

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
      "body": "75 vitamins, minerals, and whole-food sourced nutrients. Backed by science.",
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
      "pattern_ids": ["pat_morning_routine_demo"]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

## 2. Save / Bookmark Creative to Swipe File

Saves an ad creative into an organization swipe collection for team reference and remixing.

```http
POST /api/creatives/{creative_id}/save?collection=Q4_Hooks
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response

```json
{
  "status": "saved",
  "creative_id": "crt_01j7b9k2x8r4e",
  "collection": "Q4_Hooks",
  "saved_at": "2026-09-14T12:15:00Z"
}
```

To remove an item from your saved swipe files:

```http
DELETE /api/creatives/{creative_id}/save
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 3. Generate Deep Creative Insights

Runs deep multimodal LLM analysis on a creative, extracting full transcript breakdown, visual hook categorization, objection angles, and script blueprints.

```http
POST /api/creatives/{creative_id}/generate-insights
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

> [!NOTE]
> Invoking this endpoint consumes **0.5 credits** per creative.

### Response (`Insight`)

```json
{
  "id": "ins_01j7b9k2x8r4e",
  "creative_id": "crt_01j7b9k2x8r4e",
  "hook_breakdown": {
    "type": "demonstration_with_contrast",
    "description": "Opens with split-screen showing 12 pill bottles versus a single glass of water.",
    "strength_factors": ["High contrast", "Visually clear problem agitate", "Instant resolution"]
  },
  "narrative_arc": [
    { "timestamp_sec": 0, "beat": "Pattern interrupt: pill clutter agitation" },
    { "timestamp_sec": 4, "beat": "Solution introduce: single scoop drink" },
    { "timestamp_sec": 12, "beat": "Scientific credibility: 75 nutrients" },
    { "timestamp_sec": 22, "beat": "Irresistible offer: free Vitamin D3 bonus" }
  ],
  "objections_preempted": [
    "I don't have time in the morning",
    "Supplements taste bad",
    "It's too expensive compared to multivitamins"
  ]
}
```

👉 [Media Generation Endpoints](/docs/api-reference/endpoint-media-generate)
