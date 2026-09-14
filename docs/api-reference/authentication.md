# API Reference: Authentication & Keys

The Helix Intelligence API enables programmatic access to competitive discovery runs, creative scoring models, and media generation pipelines.

All requests must be made over **HTTPS** to your workspace backend API endpoint.

---

## 1. Generating an API Key

To create and manage your API keys:
1. Log in to your workspace account.
2. Navigate to **API Keys** ([/api-keys](/api-keys)) in the sidebar.
3. Click **Create Secret Key**, provide a friendly name (e.g., `Production Scraper Bot`), and copy your key immediately.
4. Keys are prefixed with `hlx_live_` followed by high-entropy cryptographic bytes.

> [!CAUTION]
> For security, the full secret key is only displayed **once** upon creation. Store your key in an environment variable or secure secrets manager. Helix never displays your raw key again.

---

## 2. Authentication Header

Authenticate all API calls by passing your secret key in the `X-API-Key` HTTP header:

```http
X-API-Key: hlx_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

Alternatively, you can authenticate using a Bearer token:

```http
Authorization: Bearer <neon_or_jwt_token>
```

---

## 3. Example Request (cURL)

```bash
curl -X GET "https://api.helix.io/api/discovery/jobs" \
  -H "X-API-Key: hlx_live_9f83a2bc0d44e12" \
  -H "Accept: application/json"
```

---

## 4. HTTP Status Codes & Error Responses

| Status Code | Code / Meaning | Description |
| :--- | :--- | :--- |
| `200 OK` | `success` | Request succeeded. Body contains JSON payload. |
| `201 Created` | `created` | Resource created (e.g. scrape job enqueued or monitor created). |
| `400 Bad Request` | `invalid_request` | Missing or malformed parameters (e.g. empty search query). |
| `401 Unauthorized` | `not_authenticated` | Missing or invalid `X-API-Key` header. |
| `403 Forbidden` | `user_banned` / `user_suspended` | Key belongs to a suspended or banned account. |
| `404 Not Found` | `not_found` | Resource identifier (e.g., `job_id`, `creative_id`) does not exist. |
| `429 Too Many Requests` | `quota_exceeded` | Daily credit quota or request limit reached. |

When an error occurs, the API returns a JSON error response:

```json
{
  "detail": {
    "code": "quota_exceeded",
    "message": "Daily credit limit of 25.0 credits reached. Resets at 00:00:00 UTC."
  }
}
```

👉 [Credit Costs & Rate Limits](/docs/api-reference/credit-costs-and-limits)
