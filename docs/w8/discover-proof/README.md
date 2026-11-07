# Discover end-to-end proof

Status: **passed on 2026-11-07** for `success`, `cancel` and `timeout`
(Metapi, Neon branch `w8-rehearsal`, local API and jobs worker as restricted
rehearsal logins). Not run against production.

## Passing runs (2026-11-07, provider cap raised to 25 for the day)

| Scenario | Query | Result | Evidence |
|---|---|---|---|
| success | Ad Library page link for Nike (`view_all_page_id`) | succeeded; Metapi returned 15 of Nike's own ads, 13 were duplicate copy, 2 stored (brand "Nike", landing `nike.com` / `nike.com.ar`, media stored in the archive) | `20261107T144827Z-success.json` |
| success | `gymshark` | succeeded; 15 returned, 3 irrelevant, 1 duplicate, 11 stored | `20261107T145038Z-success.json` |
| cancel | `adidas` | cancelled; credit refunded (net 0) | `20261107T145220Z-cancel.json` |
| timeout | `puma`, 20 s deadline | timed out at the deadline; credit refunded (net 0) | `20261107T145342Z-timeout.json` |
| success | `nike` (brand name) | succeeded with 0 kept: the 30 keyword ads came from other advertisers (most from one look-alike shop), none from a page named Nike, so the advertiser step could not resolve | `20261107T144623Z-success.json` |

Notes from these runs:

- **Big brands need the page link or page id.** Their ads rarely contain the
  brand's own name, so keyword search returns other advertisers. Smaller brands
  that name themselves (Gymshark) work by keyword.
- **Heavy de-duplication.** Ads with the same copy count once, so a brand
  reusing one text across many creatives shows few rows.
- **Archive media** was stored on temporary local disk because R2 is not
  configured; production needs R2.
- **One intermittent `500` (`TimeoutError`)** when starting a search, while the
  worker was archiving media; the retry succeeded. Cause not found yet.
- **Logging:** the worker logged full outbound URLs (signed Meta CDN links) at
  INFO. Fixed: httpx/httpcore log at WARNING; the Apify token moved from the
  URL to the Authorization header.
- Successful searches cost 0.5–1 credit; 15 of the day's 25 provider calls
  were used across all runs.

## Earlier run of 2026-11-07 (before the fixes; cap 10 provider calls)

The API and jobs worker ran locally as restricted rehearsal logins. Evidence
files `20261107T14*-success.json` are from this run.

| Attempt | Query | Result | What it showed |
|---|---|---|---|
| 1 | `nike` | failed, `provider_outage`, refunded | Every Metapi results read failed: safe_fetch decoded gzip twice. Fixed. |
| 2 | `nike` | succeeded, 0 ads kept | Metapi returned 15 ads; the relevance filter dropped all 15 |
| 3 | `nike` | succeeded, 0 ads kept | Same; filter counts now logged: `irrelevant=15` |
| 4 | `nike.com` | succeeded, 0 ads kept | Same |
| diagnostic | `nike` | no data | Metapi was still running after 25 polls; the old code then read results (409). Fixed. |
| 5 | `gymshark` | refused (429) | The trial plan's daily limit (3.5 credits) counted refunded searches |

Findings:

- **Data arrives.** Metapi accepts the task and returns ads through the
  durable worker. Credits for failed searches are refunded.
- **Keyword search is mostly look-alike sellers.** A replay of an older stored
  Metapi response shows the same: ads from pages like resellers whose text does
  not mention the brand. Helix's relevance filter correctly drops them, so a
  brand query can end with zero ads. To show a brand's own ads, Discover needs
  Metapi's `advertiser_id` search (or a pasted Ad Library page link).
- **Each task used to collect 50 ads** (Metapi's default) while Helix kept 15.
  The request now sends `count` and `keyword_exact_phrase`.
- **Refunded searches still use up the daily allowance.** Not fixed yet.
- **Follow-up (same day):** a brand query now resolves the brand's own
  advertiser page and loads its ads (Metapi `advertiser_id`); a page id or Ad
  Library page link goes straight there. Not yet run against Metapi.

Not run yet: `cancel`, `timeout`, and a `success` that stores ads.

`backend/scripts/prove_discover.py` drives a **local** API and the jobs worker
over HTTP, the same way the browser does, against the Neon dev branch `dev-w8`
(never production; it refuses any non-loopback API). It records three
scenarios as JSON evidence here: job status timeline, final status, failure
kind, deadline, credits before/after, and a result summary (counts, platforms,
how many rows have days-active and Meta reach). No secrets are written.

## What Ziad provides

One authorized **non-production** provider key, set in the environment of both
the API and the worker (not in any committed file):

| Provider | Variables | `HELIX_PROOF_PROVIDER` |
|---|---|---|
| Metapi | `METAPI_API_KEY` | `metapi` |
| Adyntel | `ADYNTEL_API_KEY`, `ADYNTEL_EMAIL` | `adyntel` |
| Apify | `APIFY_API_TOKEN`, `APIFY_ENABLED=true` | `apify` |
| Meta Ad Library (official) | `META_ACCESS_TOKEN` | `meta_official` |

## Run

```bash
cd backend
# terminal 1: API (reads backend/.env.local -> dev-w8 as helix_api_login)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# terminal 2: worker (DATABASE_URL = helix_worker_login on dev-w8)
python workers/jobs/worker.py
# terminal 3
export HELIX_PROOF_EMAIL=... HELIX_PROOF_PASSWORD=... HELIX_PROOF_PROVIDER=metapi
python scripts/prove_discover.py --scenario success
python scripts/prove_discover.py --scenario cancel
# restart API and worker with DISCOVER_JOB_DEADLINE_S=20, then:
python scripts/prove_discover.py --scenario timeout
```

Pass criteria: `success` ends `succeeded` with at least one result;
`cancel` ends `cancelled` (credits refunded: `credits_after == credits_before`);
`timeout` ends `timed_out` with the deadline honored.
