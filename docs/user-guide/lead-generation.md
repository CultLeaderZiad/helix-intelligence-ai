# Scout · Lead Generation (Scrapling)

> **Status: live when the worker is running.** Lead Generation is the public-web
> path inside Scout. Social / Atlas (handles, enrichment, Atlas scoring) is a
> separate engine and is unchanged.

Route: **`/scout/lead-generation`** · Engine id: **`scrapling_engine`**

---

## 1. What it does

Lead Generation turns public websites into a scored lead list with provenance on
**every** email and phone:

1. You write an **ICP brief** and add **seeds** (URLs, a sitemap, a Shopify store, or a domain list).
2. The **Scrapling worker** discovers URLs, fetches them (http / stealth / dynamic), and extracts public contact fields.
3. The pipeline **enriches** (website evidence first, Hunter BYOK optional), **dedupes**, and **scores** each lead against your ICP.
4. Outreach **drafts** are written only when a lead scores at or above your threshold **and** a real email or phone exists.
5. Export **CSV / JSONL** with provenance columns, or open a markdown digest artifact per page.

## 2. Engines (Scrapling capability map)

| Engine | Scrapling class | Use for |
|---|---|---|
| `http` | `Fetcher` | Fast TLS-impersonated fetches of plain sites |
| `stealth` (default) | `StealthyFetcher` | Unknown sites, Cloudflare-style challenges |
| `dynamic` | `DynamicFetcher` | JS-heavy pages (Playwright; slowest) |

Sessions are reused per job/site, AutoThrottle is always on, and a built-in
ad-block plus your deny-list keep fetches clean.

## 3. Modes

`crawl` · `sitemap` · `shopify` · `csv_feed` · `digest`

- **crawl** — follow same-domain links that match the recipe allow-list (e.g. `/contact`, `/about`, `اتصل`).
- **sitemap** — parse `sitemap.xml` (one index level deep) and crawl bounded.
- **shopify** — products index + `/pages/contact` + `/pages/about`.
- **digest** — fetch pricing/policy-style pages and store a **markdown digest artifact**.
- **csv_feed** — treat your domain list as the queue.

## 4. Recipes

Recipes are JSON files under `backend/app/data/leadgen_recipes/` and are listed by
`GET /api/scout/leadgen/recipes`:

| Recipe | Mode | Engine |
|---|---|---|
| `mena-construction-contact` | crawl | stealth |
| `clinic-beauty-mena` | crawl | stealth |
| `shopify-brand` | shopify | http |
| `competitor-pricing-digest` | digest | dynamic |
| `directory-outbound` | crawl | stealth |
| `sitemap-company-crawl` | sitemap | http |

Selecting a recipe adopts its mode, engine, page cap, and adaptive setting.

## 5. Honesty rules you can rely on

- **No fabricated contacts.** If extraction finds nothing, fields stay empty and `extract_status` says so.
- **Provenance on every contact.** `email_source` and `phone_source` are `website`, `hunter`, `bio`, or `none`.
- **Real progress only.** Job logs are the worker's actual output (`> fetch · {url} · ok`); stages and counters come from the job row.
- **Worker offline = honest error.** Nothing is queued and no leads are shown — there is no simulated success.
- **Outreach is drafted, never sent.** Helix has no send capability for outreach.

## 6. Legality & robots

`robots_txt_obey` is **on by default**. Turning it off requires the explicit job
flag and writes an audit line into the job log:

```
> audit · robots_obey=false · user=… · job=…
```

Only public pages are fetched. Localhost, RFC1918/private IPs, and non-http(s)
schemes are rejected at enqueue. Use proxies at your own cost and only where the
site's terms permit.

## 7. Credits

Charged **at enqueue** (admins bypass):

```
cost = SCRAPLING_CREDIT_BASE
     + (estimated_pages x SCRAPLING_CREDIT_PER_PAGE)
     + (enrich_emails ? 0.25 x max_leads : 0)
     + (generate_outreach ? 0.1 x max_leads : 0)
```

If the budget is exhausted mid-job the job **pauses loudly** with an explicit
message instead of silently continuing.

## 8. Pause & resume

`POST /jobs/{id}/pause` saves a checkpoint (`SCRAPLING_CHECKPOINT_DIR`) with the
pending URL queue. `POST /jobs/{id}/resume` re-queues the job and the worker
continues from that checkpoint.

## 9. Export columns

`id, company_name, website, domain, emails, phones, socials, address,
email_source, phone_source, extract_status, fetch_status, engine_used,
lead_score, priority, decision_makers, outreach_subject,
markdown_artifact_path, source_urls`

A job with zero leads exports **headers only** — honest emptiness, not filler rows.

## 10. Running the worker

See `backend/workers/scrapling/README.md`:

```bash
pip install "scrapling[fetchers]" && scrapling install
export SCRAPLING_WORKER_ENABLED=true
python workers/scrapling/worker.py
```

Or deploy the official image (`ghcr.io/d4vinci/scrapling:latest`) with the
provided Dockerfile. The API process never imports Scrapling, so the web service
boots without browsers.

## 11. Scoring formula

```
score = 30 (real email) + 20 (real phone) + 15 (company name)
      + 10 (address) + 10 (contact-page signal) + 10 (decision-maker hints)
      + min(15, 5 x unique ICP keyword overlaps)   -> clamp 0..100
priority: high >= 70 | med 40-69 | low < 40
```

Deterministic first; LLM assistance never invents contact fields.
