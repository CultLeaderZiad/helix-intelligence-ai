import { request } from "../http"

/**
 * FastAPI-backed discovery service.
 *
 * Written up front and intentionally thin. Because it satisfies the same
 * interface as discoverService.mock.js, switching VITE_DATA_SOURCE=api
 * requires zero component or hook changes.
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
    const { query = "", filters = {}, sort = "composite_desc", query_language = "en" } = params
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
   * @param {{page?: number, page_size?: number, sort?: string}} [params]
   * @param {{signal?: AbortSignal}} [options]
   */
  getJobResults(jobId, { page = 1, page_size = 20, sort } = {}, { signal } = {}) {
    return request(`/discovery/jobs/${encodeURIComponent(jobId)}/results`, {
      signal,
      params: { page, page_size, sort },
    })
  },

  listRecentJobs() {
    return request("/discovery/jobs", { params: { page: 1, page_size: 8 } })
  },
}

export default discoverService
