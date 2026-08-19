import { creatives } from "@/data/creatives"
import { brandsById } from "@/data/brands"
import { DISCOVERY_STAGES, recentJobs } from "@/data/jobs"
import { ServiceError } from "../http"
import { delay, maybeFail, makeId } from "./latency"

/**
 * Mock discovery service.
 *
 * Simulates a worker-backed scrape: `search()` does NOT return creatives.
 * It enqueues a job and returns a handle immediately, exactly as the
 * FastAPI endpoint will. The client then polls `getJobStatus()` and only
 * calls `getJobResults()` once the job reports `succeeded`.
 *
 * Progress is derived from elapsed wall-clock against stage weights, so
 * it survives component remounts and is never a CSS-only illusion — the
 * numbers the UI renders come from this service.
 */

/** @type {Map<string, any>} */
const jobStore = new Map()

const TOTAL_WEIGHT = DISCOVERY_STAGES.reduce((sum, s) => sum + s.weight, 0)

/* ------------------------------------------------------------------ */
/* Query engine — stands in for what SQL/Elastic will do server-side  */
/* ------------------------------------------------------------------ */

function matchesQuery(creative, query) {
  if (!query) return true
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  const brand = brandsById[creative.brand_id]
  const haystack = [
    creative.headline,
    creative.body,
    creative.cta,
    creative.landing_domain,
    brand?.name,
    brand?.category,
    ...(creative.pattern_ids ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()

  // Support quoted phrases; otherwise every term must appear.
  const phrases = [...needle.matchAll(/"([^"]+)"/g)].map((m) => m[1])
  const rest = needle.replace(/"[^"]+"/g, " ")
  const terms = rest.split(/\s+/).filter(Boolean)

  return (
    phrases.every((p) => haystack.includes(p)) &&
    terms.every((t) => haystack.includes(t))
  )
}

function matchesFilters(creative, filters = {}) {
  const {
    platforms = [],
    formats = [],
    spend_bands = [],
    min_score = null,
    min_days_active = null,
  } = filters

  if (platforms.length && !platforms.includes(creative.platform)) return false
  if (formats.length && !formats.includes(creative.format)) return false
  if (spend_bands.length && !spend_bands.includes(creative.metrics?.spend_band))
    return false
  if (min_score !== null && min_score > 0) {
    const composite = creative.scores?.composite
    if (composite === null || composite === undefined) return false
    if (composite < min_score) return false
  }
  if (min_days_active !== null && min_days_active > 0) {
    if ((creative.days_active ?? 0) < min_days_active) return false
  }
  return true
}

const SORTERS = {
  composite_desc: (a, b) => (b.scores?.composite ?? -1) - (a.scores?.composite ?? -1),
  hook_desc: (a, b) => (b.scores?.hook ?? -1) - (a.scores?.hook ?? -1),
  days_active_desc: (a, b) => (b.days_active ?? 0) - (a.days_active ?? 0),
  first_seen_desc: (a, b) => new Date(b.first_seen) - new Date(a.first_seen),
  impressions_desc: (a, b) =>
    (b.metrics?.impressions_est ?? 0) - (a.metrics?.impressions_est ?? 0),
}

function runQuery({ query, filters, sort }) {
  const matched = creatives.filter(
    (c) => matchesQuery(c, query) && matchesFilters(c, filters),
  )
  const sorter = SORTERS[sort] ?? SORTERS.composite_desc
  return [...matched].sort(sorter)
}

/* ------------------------------------------------------------------ */
/* Job progress derivation                                            */
/* ------------------------------------------------------------------ */

function deriveJob(record) {
  const now = Date.now()
  const elapsed = now - record.started_at

  if (record.forced_error) {
    return {
      job_id: record.job_id,
      status: "failed",
      progress: record.fail_at_progress,
      stage: record.fail_stage,
      stage_label:
        DISCOVERY_STAGES.find((s) => s.key === record.fail_stage)?.label ?? "Failed",
      stage_index: DISCOVERY_STAGES.findIndex((s) => s.key === record.fail_stage),
      stages_total: DISCOVERY_STAGES.length,
      records_found: 0,
      elapsed_ms: elapsed,
      created_at: record.created_at,
      completed_at: new Date(record.started_at + record.duration_ms).toISOString(),
      error: record.forced_error,
    }
  }

  const ratio = Math.min(1, elapsed / record.duration_ms)

  // Walk the weighted stage list to find where `ratio` lands.
  let cumulative = 0
  let stageIndex = 0
  for (let i = 0; i < DISCOVERY_STAGES.length; i += 1) {
    const share = DISCOVERY_STAGES[i].weight / TOTAL_WEIGHT
    if (ratio <= cumulative + share || i === DISCOVERY_STAGES.length - 1) {
      stageIndex = i
      break
    }
    cumulative += share
  }

  const done = ratio >= 1
  const stage = done
    ? DISCOVERY_STAGES[DISCOVERY_STAGES.length - 1]
    : DISCOVERY_STAGES[stageIndex]

  // Records stream in during enumeration/fetching rather than all at once.
  const discoveryRatio = Math.min(1, ratio / 0.85)
  const recordsFound = done
    ? record.total_records
    : Math.floor(record.total_records * discoveryRatio)

  return {
    job_id: record.job_id,
    status: done ? "succeeded" : ratio > 0.05 ? "running" : "queued",
    progress: Number(ratio.toFixed(4)),
    stage: stage.key,
    stage_label: stage.label,
    stage_index: done ? DISCOVERY_STAGES.length - 1 : stageIndex,
    stages_total: DISCOVERY_STAGES.length,
    records_found: recordsFound,
    elapsed_ms: Math.round(elapsed),
    created_at: record.created_at,
    completed_at: done
      ? new Date(record.started_at + record.duration_ms).toISOString()
      : null,
    error: null,
  }
}

/* ------------------------------------------------------------------ */
/* Public interface — must match discoverService.api.js exactly       */
/* ------------------------------------------------------------------ */

const discoverService = {
  /**
   * Enqueue a discovery job.
   * @param {import('../contracts').SearchParams} params
   * @returns {Promise<import('../contracts').Job>}
   */
  async search(params = {}) {
    await delay(220)
    maybeFail("Could not reach discovery orchestrator")

    const { query = "", filters = {}, sort = "composite_desc" } = params
    const results = runQuery({ query, filters, sort })

    const jobId = makeId("job")
    const nowIso = new Date().toISOString()

    // A query that matches nothing still runs a job and completes empty —
    // "no results" is a valid outcome, not an error.
    const record = {
      job_id: jobId,
      query,
      filters,
      sort,
      result_ids: results.map((c) => c.id),
      total_records: results.length,
      created_at: nowIso,
      started_at: Date.now(),
      duration_ms: 3200 + Math.random() * 2600,
      forced_error: null,
      fail_stage: null,
      fail_at_progress: 0,
    }

    // Deterministic failure rehearsal: a reserved query trips the error path
    // so the UI's failed-job branch is reachable without editing code.
    if (query.trim().toLowerCase() === "fail") {
      record.forced_error = "Upstream rate limit reached for source: meta_ad_library"
      record.fail_stage = "enumerating"
      record.fail_at_progress = 0.34
      record.duration_ms = 1400
    }

    jobStore.set(jobId, record)
    return deriveJob(record)
  },

  /**
   * Poll a job. Cheap and idempotent.
   * @param {string} jobId
   * @returns {Promise<import('../contracts').Job>}
   */
  async getJobStatus(jobId) {
    await delay(90)
    const record = jobStore.get(jobId)
    if (!record) {
      throw new ServiceError(`Job ${jobId} not found`, {
        status: 404,
        code: "job_not_found",
      })
    }
    return deriveJob(record)
  },

  /**
   * Fetch a page of a completed job's results.
   * @param {string} jobId
   * @param {{ page?: number, page_size?: number, sort?: string }} [opts]
   * @returns {Promise<import('../contracts').Paginated>}
   */
  async getJobResults(jobId, opts = {}) {
    const started = performance.now()
    await delay()
    maybeFail("Result index temporarily unavailable")

    const record = jobStore.get(jobId)
    if (!record) {
      throw new ServiceError(`Job ${jobId} not found`, {
        status: 404,
        code: "job_not_found",
      })
    }

    const derived = deriveJob(record)
    if (derived.status === "failed") {
      throw new ServiceError(derived.error, { status: 502, code: "job_failed" })
    }
    if (derived.status !== "succeeded") {
      throw new ServiceError("Job has not completed", {
        status: 409,
        code: "job_incomplete",
      })
    }

    const { page = 1, page_size = 20, sort } = opts

    let items = record.result_ids
      .map((id) => creatives.find((c) => c.id === id))
      .filter(Boolean)

    // Re-sorting a completed result set must not require a new scrape.
    if (sort && SORTERS[sort]) items = [...items].sort(SORTERS[sort])

    const total = items.length
    const start = (page - 1) * page_size
    const paged = items.slice(start, start + page_size)

    return {
      items: paged,
      total,
      page,
      page_size,
      has_more: start + page_size < total,
      took_ms: Math.round(performance.now() - started),
    }
  },

  /**
   * Job history for the status bar / activity drawer.
   * @returns {Promise<import('../contracts').Paginated>}
   */
  async listRecentJobs() {
    await delay(140)
    const live = [...jobStore.values()]
      .map(deriveJob)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 5)
      .map((j) => ({
        job_id: j.job_id,
        query: jobStore.get(j.job_id)?.query ?? "",
        status: j.status,
        records_found: j.records_found,
        created_at: j.created_at,
        completed_at: j.completed_at,
        duration_ms: j.elapsed_ms,
        error: j.error,
      }))

    const items = [...live, ...recentJobs].slice(0, 8)
    return {
      items,
      total: items.length,
      page: 1,
      page_size: items.length,
      has_more: false,
    }
  },
}

export default discoverService
