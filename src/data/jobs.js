/**
 * Scrape / discovery job fixtures.
 *
 * `DISCOVERY_STAGES` is the canonical pipeline the backend worker will
 * report against. Weights sum to 1.0 and describe the share of total
 * wall-clock each stage typically consumes — the mock service uses them
 * to derive progress, and the real worker will report the same stage keys.
 */

export const DISCOVERY_STAGES = [
  { key: "queued", label: "Queued", weight: 0.05 },
  { key: "resolving_sources", label: "Resolving sources", weight: 0.1 },
  { key: "enumerating", label: "Enumerating ad library", weight: 0.28 },
  { key: "fetching_assets", label: "Fetching creative assets", weight: 0.27 },
  { key: "scoring", label: "Scoring creatives", weight: 0.22 },
  { key: "indexing", label: "Indexing results", weight: 0.08 },
]

/** Recent job history — populates the status bar and the job drawer. */
export const recentJobs = [
  {
    job_id: "job_7c1e44",
    query: "skincare routine reduction",
    status: "succeeded",
    records_found: 214,
    created_at: "2026-08-18T09:12:00Z",
    completed_at: "2026-08-18T09:12:41Z",
    duration_ms: 41200,
  },
  {
    job_id: "job_7c1e39",
    query: "pet food blind test",
    status: "succeeded",
    records_found: 88,
    created_at: "2026-08-18T08:44:00Z",
    completed_at: "2026-08-18T08:44:29Z",
    duration_ms: 29400,
  },
  {
    job_id: "job_7c1e31",
    query: "b2b finance close",
    status: "failed",
    records_found: 0,
    created_at: "2026-08-17T17:20:00Z",
    completed_at: "2026-08-17T17:20:12Z",
    duration_ms: 12100,
    error: "Upstream rate limit reached for source: linkedin_ads",
  },
]
