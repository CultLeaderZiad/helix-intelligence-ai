# Helix Intelligence — Technical Documentation

## Table of Contents
1. [Trial & Quota System](#trial--quota-system)
2. [Provider Chain & Fallback Order](#provider-chain--fallback-order)
3. [AI Router](#ai-router)
4. [Data Flow](#data-flow)
5. [API Reference](#api-reference)

---

## Trial & Quota System

### Overview
Helix Intelligence uses a **dual-limit quota system** for trial users:
- **Total Credit Quota**: Fixed allowance for the entire 7-day trial
- **Daily Credit Limit**: Per-day spending cap to prevent resource exhaustion

### Credit Allocation

| Plan | Total Credits | Daily Limit | Duration | Cost Per Credit |
|------|--------------|-------------|----------|-----------------|
| Trial (default) | 25 | 4.0 | 7 days | Free |
| Pay-as-you-go | Custom | Unlimited | Ongoing | $0.01 |

### How Daily Limits Work

1. **UTC Midnight Boundary**: Daily counters reset at 00:00:00 UTC
2. **Atomic Reset**: The `_ensure_daily_reset()` function checks if the current UTC day has changed and resets the counter
3. **Double Gate**: Both daily AND total limits must pass before an action is allowed

```
User Action → check_quota_and_feature()
  ├─ 1. Check Trial Expiration (HTTP 403: TRIAL_EXPIRED)
  ├─ 2. Check Feature Flags (HTTP 403: FEATURE_DISABLED)
  ├─ 3. Check Daily Limit (HTTP 429: DAILY_LIMIT_REACHED)
  └─ 4. Check Total Balance (HTTP 402: CREDIT_LIMIT_REACHED)
```

### Error Responses

| Code | Status | Meaning |
|------|--------|---------|
| `TRIAL_EXPIRED` | 403 | 7-day trial ended |
| `FEATURE_DISABLED` | 403 | Feature not in plan |
| `DAILY_LIMIT_REACHED` | 429 | Daily cap hit, resets at UTC midnight |
| `CREDIT_LIMIT_REACHED` | 402 | Total balance exhausted |

### Database Schema

**organizations table** (denormalized for fast reads):
```sql
daily_credits_used_today FLOAT DEFAULT 0.0
daily_credits_reset_at   TIMESTAMP  -- last UTC midnight when reset occurred
```

**plans table**:
```sql
daily_credit_limit FLOAT  -- NULL = unlimited (paid plans)
```

---

## Provider Chain & Fallback Order

### Scraping Providers (Ad Intelligence)

The system uses a **chain-of-responsibility pattern** with automatic fallback:

```
Priority 1: Meta Ad Library API (Official)
  ↓ if rate-limited or unavailable
Priority 2: Bright Data (Web Scraping)
  ↓ if blocked or timeout
Priority 3: Apify (Backup Scraping)
  ↓ if all fail
Priority 4: ScrapeGraph AI (Smart Extraction)
```

#### Provider Details

| Provider | Type | Use Case | Est. Cost |
|----------|------|----------|-----------|
| Meta Official | API | Direct ad library access | Free (rate-limited) |
| Bright Data | Proxy | Residential IP scraping | ~$0.003/request |
| Apify | Cloud Actor | Structured extraction | ~$0.75/1k ads |
| ScrapeGraph | AI | Landing page parsing | ~$0.005/page |

#### RawCreative Schema (Standardized Output)

All providers normalize to this schema:

```python
class RawCreative(BaseModel):
    platform: str                    # 'facebook' | 'instagram' | 'tiktok'
    brand_name: str
    headline: Optional[str]
    body: Optional[str]
    cta: Optional[str]
    data_source: str                 # 'meta_official' | 'ad_library_scrape' | 'organic_content_proxy'
    is_estimated: bool = True        # True if metrics are estimated, not official
    impressions_est: Optional[int]   # Estimated impressions
    # ... other fields
```

### Normalization Pipeline

Raw provider output → `normalize_creatives()`:
1. Deduplication by `(platform, brand_name, headline, body)`
2. Metric estimation (if not provided by source)
3. Format standardization (video/image/carousel)

---

## AI Router

### Multi-Tier Provider Chain

The AI router provides **automatic failover** across multiple LLM providers:

```
Tier 1: Groq (Primary)
  ↓ if rate-limited (429) or error
Tier 2: OpenRouter (Fallback)
  ↓ if unavailable
Tier 3: Gemini (Tertiary)
  ↓ if all fail
Raise: "All AI providers failed"
```

#### Provider Configuration

| Tier | Provider | Model | Use Case |
|------|----------|-------|----------|
| 1 | Groq | GPT-OSS-120B | Primary (fastest, cheapest) |
| 2 | OpenRouter | Varies | Fallback (more models) |
| 3 | Gemini | Gemini Pro | Last resort |

#### Trial Mode Restrictions

Trial users have additional constraints:
- **Daily Request Limit**: 20 requests/day (enforced via `UsageLog` count)
- **Provider Access**: Limited to trial-eligible providers
- **BYOK Option**: Users can provide their own API key to bypass limits

### Usage Logging

Every AI call creates a `UsageLog` entry:

```python
UsageLog(
    user_id, org_id, job_id,
    provider="groq",
    operation="ai_analysis",
    units=1500,              # tokens or credits
    cost_usd=0.0009,         # estimated cost
    credits_deducted=0.5,    # credit cost to user
    tokens_used=1500,
    requests_used=1,
    metadata_json={"model": "groq/llama-3.3-70b", "temperature": 0.7}
)
```

---

## Data Flow

### End-to-End Pipeline

```
User Search Query
       ↓
┌─────────────────────────────────────────┐
│  1. DISCOVER PHASE                      │
│  - Search query → Provider chain        │
│  - Scrape ad libraries                  │
│  - Return RawCreative[]                 │
│  - Credit cost: 2.0 credits            │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  2. INTELLIGENCE PHASE                  │
│  - AI analysis of creatives             │
│  - Score: hook, clarity, retention      │
│  - Extract patterns & insights          │
│  - Credit cost: 1.0 credit             │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  3. CREATE PHASE                        │
│  - Generate new creative concepts       │
│  - AI-powered ideation                  │
│  - Credit cost: 0.5 credits            │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  4. PERFORMANCE PHASE                   │
│  - Track creative performance           │
│  - Compare against benchmarks           │
│  - Optimization recommendations         │
└─────────────────────────────────────────┘
```

### Credit Costs by Action

| Action | Credits | Provider |
|--------|---------|----------|
| Discovery Search | 2.0 | Scraping providers |
| Pattern Analysis | 1.0 | AI router |
| AI Chat/Generation | 0.5 | AI router |
| Swipe File Save | 0.0 | Local storage |

### Data Persistence

| Data Type | Storage | Retention |
|-----------|---------|-----------|
| Raw Creatives | PostgreSQL | Permanent |
| AI Analysis | PostgreSQL | Permanent |
| Usage Logs | PostgreSQL | Permanent |
| User Sessions | JWT + localStorage | 24 hours |
| Organization | PostgreSQL | Permanent |

---

## API Reference

### Authentication

All protected endpoints require:
```
Authorization: Bearer <jwt_token>
```

### Key Endpoints

| Endpoint | Method | Credits | Description |
|----------|--------|---------|-------------|
| `/api/discovery/search` | POST | 2.0 | Search ad libraries |
| `/api/discovery/jobs` | GET | 0 | List search jobs |
| `/api/creatives` | GET | 0 | List discovered creatives |
| `/api/analysis/patterns` | GET | 0 | Get analysis patterns |
| `/api/insights/` | GET | 0 | Get insights |
| `/api/account/trial-status` | GET | 0 | Check trial/quota status |
| `/api/account/billing` | GET | 0 | Get billing summary |
| `/api/notifications` | GET | 0 | Get notifications |

### Error Response Format

```json
{
  "code": "DAILY_LIMIT_REACHED",
  "message": "Daily credit limit reached (4.0/day)...",
  "daily_limit": 4.0,
  "daily_used": 3.5,
  "daily_remaining": 0.5,
  "resets_at_utc": "2026-08-26T00:00:00+00:00",
  "plan_name": "Trial Plan"
}
```

---

## Environment Variables

See `.env.example` for required configuration:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key |
| `DATABASE_URL` | ✅ | Neon Postgres connection |
| `META_ACCESS_TOKEN` | For live data | Meta Graph API token |
| `BRIGHTDATA_API_KEY` | For scraping | Bright Data proxy |
| `APIFY_API_TOKEN` | For scraping | Apify cloud actors |
| `GROQ_API_KEY` | For AI | Groq inference |
| `OPENROUTER_API_KEY` | For AI | OpenRouter fallback |

---

## Architecture Decisions

### Why Dual Limits?

1. **Resource Protection**: Free-tier providers (Groq) have daily quotas
2. **Fair Usage**: Prevents single user from exhausting shared pool
3. **Predictable Costs**: Daily cap ensures budget compliance

### Why Denormalized Daily Counter?

- **Performance**: Avoids scanning `UsageLog` on every request
- **Atomic Reset**: Simple timestamp check vs. complex aggregation
- **Trade-off**: Slight data staleness acceptable for speed

### Why UTC Midnight?

- **Simplicity**: No timezone confusion
- **Consistency**: All users reset at same time globally
- **Alignment**: Matches most API provider reset cycles

---

*Last updated: 2026-08-25*
