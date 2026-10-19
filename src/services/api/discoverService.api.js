import { request } from "../http"

/**
 * FastAPI-backed discovery service.
 *
 * Written up front and intentionally thin. Because it satisfies the same
 * interface as discoverService.mock.js, switching VITE_DATA_SOURCE=api
 * requires zero component or hook changes.
 *
 * Expected endpoints:
 *   POST /v1/discovery/jobs         -> Job
 *   GET  /v1/discovery/jobs/{id}    -> Job
 *   GET  /v1/discovery/jobs/{id}/results -> Paginated<Creative>
 *   GET  /v1/discovery/jobs         -> Paginated<Job>
 */
const discoverService = {
  search(params = {}, { signal } = {}) {
    const { query = "", filters = {}, sort = "composite_desc", query_language = "en" } = params
    const finalQuery = query.trim() || "*"
    return request("/discovery/jobs", {
      method: "POST",
      signal,
      body: { query: finalQuery, filters, sort, query_language },
    })
  },

  getJobStatus(jobId, { signal } = {}) {
    return request(`/discovery/jobs/${jobId}`, { signal })
  },

  getJobResults(jobId, { page = 1, page_size = 20, sort } = {}, { signal } = {}) {
    return request(`/discovery/jobs/${jobId}/results`, {
      signal,
      params: { page, page_size, sort },
    })
  },

  listRecentJobs() {
    return request("/discovery/jobs", { params: { page: 1, page_size: 8 } })
  },
}

export default discoverService
