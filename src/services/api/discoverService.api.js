import { request } from "../http"

/**
 * FastAPI-backed discovery service. Intentionally thin.
 *
 * Expected endpoints:
 *   POST /api/discovery/jobs         -> Job
 *   GET  /api/discovery/jobs/{id}    -> Job
 *   POST /api/discovery/jobs/{id}/cancel -> Job or cancellation acknowledgement
 *   GET  /api/discovery/jobs/{id}/results -> Paginated<Creative>
 *   GET  /api/discovery/jobs         -> Paginated<Job>
 */
const discoverService = {
  /**
   * @param {import('../contracts').SearchParams} [params]
   * @param {{signal?: AbortSignal}} [options]
   */
  search(params = {}, { signal } = {}) {
    const { query = "", filters = {}, sort = "days_active_desc", query_language = "en" } = params
    const finalQuery = query.trim() || "*"
    return request("/discovery/jobs", {
      method: "POST",
      signal,
      body: { query: finalQuery, filters, sort, query_language },
    })
  },

  /** @param {string} jobId @param {{signal?: AbortSignal}} [options] */
  getJobStatus(jobId, { signal } = {}) {
    return request(`/discovery/jobs/${encodeURIComponent(jobId)}`, { signal })
  },

  /** @param {string} jobId */
  cancelJob(jobId) {
    return request(`/discovery/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST",
    })
  },

  /**
   * @param {string} jobId
   * @param {{page?: number, page_size?: number, sort?: string, min_days?: number, min_score?: number}} [params]
   * @param {{signal?: AbortSignal}} [options]
   */
  getJobResults(jobId, { page = 1, page_size = 20, sort, min_days = 0, min_score = 0 } = {}, { signal } = {}) {
    // View filters apply to stored results; 0 means "not set" and is omitted.
    const params = { page, page_size, sort }
    if (min_days > 0) params.min_days = min_days
    if (min_score > 0) params.min_score = min_score
    return request(`/discovery/jobs/${encodeURIComponent(jobId)}/results`, { signal, params })
  },

  listRecentJobs() {
    return request("/discovery/jobs", { params: { page: 1, page_size: 8 } })
  },
}

export default discoverService
