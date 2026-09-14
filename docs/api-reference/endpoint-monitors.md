# API Reference: Monitors Endpoints

The Monitors API allows you to automate recurring competitor tracking, receive alert feeds, and stream detected ad events into your own webhooks.

---

## 1. Create a Scheduled Monitor

Registers a recurring background monitoring loop for a competitor brand or market query.

```http
POST /api/monitors
Content-Type: application/json
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Request Body (`MonitorCreate`)

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `query` | `string` | **Yes** | — | Competitor brand name or search phrase (1–300 chars). |
| `name` | `string` | No | `""` | Friendly label for this monitor. |
| `cadence` | `string` | No | `"daily"` | Scheduling cadence: `"daily"` or `"weekly"`. |
| `filters` | `object` | No | `{}` | Optional ad library filter criteria. |
| `notify_in_app` | `boolean` | No | `true` | Post alerts to in-app notification feed. |
| `notify_email` | `boolean` | No | `false` | Send email digests on new creative detections. |

#### Example Request

```json
{
  "query": "Ridge Wallet",
  "name": "Ridge Daily Competitive Tracker",
  "cadence": "daily",
  "filters": {
    "platform": "meta",
    "format": "video"
  },
  "notify_in_app": true,
  "notify_email": true
}
```

### Response (`201 Created`)

```json
{
  "id": "mon_01j7b9k2x4p0m",
  "name": "Ridge Daily Competitive Tracker",
  "query": "Ridge Wallet",
  "cadence": "daily",
  "status": "active",
  "filters": {
    "platform": "meta",
    "format": "video"
  },
  "notify_in_app": true,
  "notify_email": true,
  "last_run_at": null,
  "next_run_at": "2026-09-15T00:00:00Z",
  "created_at": "2026-09-14T12:30:00Z"
}
```

---

## 2. List Configured Monitors

Retrieve all active and paused competitor monitors for your organization.

```http
GET /api/monitors
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response

```json
[
  {
    "id": "mon_01j7b9k2x4p0m",
    "name": "Ridge Daily Competitive Tracker",
    "query": "Ridge Wallet",
    "cadence": "daily",
    "status": "active",
    "last_run_at": "2026-09-14T02:15:00Z",
    "events_count": 14,
    "created_at": "2026-09-10T08:00:00Z"
  }
]
```

---

## 3. List Monitor Event Stream

Query new creative detections, evergreen milestones, and fatigue alerts triggered by your monitors.

```http
GET /api/monitors/events?monitor_id=mon_01j7b9k2x4p0m&limit=50
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Response

```json
[
  {
    "id": "evt_9831a2",
    "monitor_id": "mon_01j7b9k2x4p0m",
    "event_type": "new_creative_detected",
    "creative_id": "crt_01j7b9k2x8r4e",
    "title": "New Video Ad: Ridge Carbon Fiber Drop",
    "summary": "Ridge launched a new 9:16 vertical hook focusing on RFID protection with high Hook Score (92/100).",
    "detected_at": "2026-09-14T02:15:10Z"
  }
]
```

👉 [Authentication & Headers](/docs/api-reference/authentication)
