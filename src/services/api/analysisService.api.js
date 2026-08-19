import { request } from "../http"

/**
 * Expected endpoints:
 *   GET /v1/creatives/{id}/insights -> Paginated<Insight>
 *   GET /v1/insights                -> Paginated<Insight>
 */
const analysisService = {
  getInsight(creativeId) {
    return request(`/creatives/${creativeId}/insights`)
  },

  listInsights({ page = 1, page_size = 20 } = {}) {
    return request("/insights", { params: { page, page_size } })
  },
}

export default analysisService
