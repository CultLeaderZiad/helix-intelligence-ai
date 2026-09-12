# Helix Intelligence — updates (12 Sep 2026)

## Latest pushed commit (GitHub `main`)

**HEAD:** https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/4e49a95c81387ae8501ba6871fdcdcca4970d8e6  
(merge of PR #13 — Discover `NameError`)

**Product commit (this session):** https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/b6c42ea02d320ae6156b5e582c2e7ccfd0a85590  
`Ship live Discover, monitors, and English/Arabic query translation.`

**Branch:** https://github.com/CultLeaderZiad/helix-intelligence-ai/tree/main

| Surface | URL |
|---|---|
| Frontend (Vercel) | https://helix-intelligence-ai-six.vercel.app |
| Backend (Render) | https://helix-intelligence-ai.onrender.com |
| Health | https://helix-intelligence-ai.onrender.com/api/health |

A follow-up commit on this file also lands media-job scoping, real job cancel, and a generic sign-in 500 body. After that push, HEAD will move; `b6c42ea` remains the Discover/Monitors commit.

---

## Public deploy verdict

**The `main` codebase is ready to serve the public product loop** (Discover cache fix, NameError fix, simulation, monitors, EN/AR). **Live Render is not yet ready for Metapi keyword search.**

Probed `GET /api/health` on 12 Sep 2026 evening UTC+3:

- `USE_MOCKS: false` — good
- `db: connected` — good
- `METAPI_API_KEY: false` — **the running worker still has no Metapi key**
- `ADYNTEL_API_KEY`, `META_ACCESS_TOKEN`, `APIFY_API_TOKEN`: true
- Health **lists** `METAPI_API_KEY`, which means the `b6c42ea` health router **is** on Render. The env var is just unset in that process.

Until you paste `METAPI_API_KEY` on Render and **Manual Deploy / Restart**, keyword Discover still skips Metapi. Adyntel only runs for domain-shaped queries (`nike.com`). Meta Graph / Apify may still return empty for commercial keywords.

Do **not** merge PR **#14** or the Hoplite `teos-…-remove-adyntel-apify-higgsfield` branch into `main`.

---

## Cross-check vs Antigravity (PRs #11–#14)

Antigravity’s high-level PR table is **correct**:

| PR | Topic | State | On `main`? |
|---|---|---|---|
| **#11** | Security (HMAC, IDOR, rate limit, reset-link leak) | **Still OPEN** | No (do not merge the whole PR) |
| **#12** | Audience simulation | Closed | Yes — `47992bf` |
| **#13** | `clean_query` NameError | Closed | Yes — `4c9838e` / merge `4e49a95` |
| **#14** | Delete Adyntel/Apify/Higgsfield | Merged **into the Hoplite feature branch only** | **No** |

### Where Antigravity is right

- Empty 12h cache (`record_count > 0`) and NameError are the two Discover blockers; both are on `main`.
- PR **#14** branched before `b6c42ea`. Merging that branch into `main` would fight Monitors, Resend, query translation, R2, and the current provider chain.
- Live `METAPI_API_KEY: false` until Render restart with the key.
- `CRON_SECRET` must be set or `/api/monitors/tick` is 503.
- Vercel must be on this `main` for Monitors + EN/AR in the UI.

### Where Antigravity is wrong or incomplete

- **“Leave PR #11 closed/redundant”** — #11 is **open**. Only **two** of its six items were ported locally (media IDOR + cancel). Rate limiter, webhook HMAC, Higgsfield webhook token, and `AUTH_DEV_RESET_RETURN` default-true are **still missing on `main`**.
- Those two ports were **uncommitted** until this follow-up. GitHub `4e49a95` did not include them yet.
- **“Ported into local main = public safety”** — not until that code is **pushed and Render redeploys**.
- Cancel still cannot abort an already-dispatched Higgsfield/Gemini HTTP call; it marks the row `canceled` so later writes should not present as success. PR #11’s fuller version also dropped results / skipped billing in the worker loops; this port is the router + IDOR scope only.
- Admin users can still read any media job (intentional support bypass in the local port).

**Do not merge PR #11 as-is.** It is stacked on extra commits (old Discover refunds, a `design/` roadmap) and is a large unrelated delta. Cherry-pick remaining security items later.

---

## What `b6c42ea` shipped

1. Live Discover: Metapi first, then Adyntel (domains), Meta Graph, Apify if token present.
2. 12h cache only for jobs with ads (`record_count > 0`).
3. Runtime credentials (`os.environ` first).
4. English / Arabic search toggle + Groq translate before scrape.
5. Monitors + Resend in-app/email alerts.
6. Job heartbeat + reconciliation loop (plus existing startup SQL sweep).
7. Cloudflare **R2** for generated media (storage, not scraping).
8. Intelligence / Performance use `latestSearch.items` only when a query is set.
9. Onboarding dismiss / Go to Dashboard / blank Run disabled.

---

## 1. Discover

**Bug:** “Real madrid” finished in seconds as Meta Graph only, 0 ads. Metapi never ran. Vercel `METAPI_API_KEY` does nothing (Vite `VITE_*` only). 12h cache replayed empty succeeded jobs. Domain hits then died at normalize (`clean_query` undefined).

**Fixed in code on `main`:** cache guard, NameError, honest `(not configured)` sources, EN/AR.

**Not fixed in the live worker until Metapi key + restart.**

| Service | Role |
|---|---|
| Metapi | Primary keyword search |
| Adyntel | Domain fallback only |
| Meta Graph | Official archive; weak for commercial worldwide |
| Apify | Last resort if token set |
| ScrapeGraph | Enrich landing pages **after** ads exist |
| Bright Data | Not wired as a scraper |
| Cloudflare R2 | Media files only |

---

## 2–6. Other product work

**Intelligence / Performance:** empty Discover no longer shows leftover Nike (etc.) creatives under the new query name.

**Monitors:** `POST /api/monitors/tick` + `X-Cron-Secret`. Failed runs charge like Discover (no refund) and notify. Set `APP_BASE_URL` to the Vercel origin for email links. `RESEND_API_KEY` + `RESEND_FROM` optional.

**R2:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE_URL` — all five or R2 stays off.

**Create:** Higgsfield still present; 401s are honest. Simulation panel kept. PR #14 would have deleted Higgsfield — leave it off `main`.

---

## Operational checklist before inviting the public

1. Render → Environment: `METAPI_API_KEY` set → **Manual Deploy**. Re-check health until `METAPI_API_KEY: true`.
2. Vercel production = this `main` (Monitors in the sidebar, EN/AR on Discover).
3. `CRON_SECRET` + a 15–30 min POST to `/api/monitors/tick`.
4. `APP_BASE_URL=https://helix-intelligence-ai-six.vercel.app` on Render.
5. Optional: `RESEND_*`, all five `R2_*`.
6. **Never** merge `hoplite/teos-2ceb1e05-fix-discover-nameerror--remove-adyntel-apify-higgsfield` into `main`.

### Still open (not blockers for a first public Discover, but real)

- Auth **rate limit** (PR #11) — not on `main`.
- Higgsfield / auth **webhook HMAC** — unsigned callbacks still a risk if those routes are exposed.
- `AUTH_DEV_RESET_RETURN` still defaults **true** in config — password-reset URLs can appear in API JSON unless the Render env sets it false.
- PBKDF2 on the event loop (noted in #11, deferred).

---

## Commit timeline on `main`

| SHA | What |
|---|---|
| [4e49a95](https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/4e49a95c81387ae8501ba6871fdcdcca4970d8e6) | Merge PR #13 |
| [b6c42ea](https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/b6c42ea02d320ae6156b5e582c2e7ccfd0a85590) | Discover/Monitors/EN-AR |
| [47992bf](https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/47992bf7ad95dca04a0fd97f9bbb9895a85cb000) | Create simulation (PR #12) |
| [bea7ff2](https://github.com/CultLeaderZiad/helix-intelligence-ai/commit/bea7ff2215648eb5cfb45683e0adcea913a3bb5e) | Honest-system |

Scratch `backend/scripts/_tmp_*` files stay untracked on purpose.
