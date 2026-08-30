import { request } from "../http"

/**
 * Expected endpoints:
 *   GET /v1/creatives/{id}/insights -> Paginated<Insight>
 *   POST /v1/creatives/{id}/generate-insights -> Insight (1.0 credit)
 *   GET /v1/insights                -> Paginated<Insight>
 *   POST /v1/patterns/generate      -> List<Pattern>
 */
const analysisService = {
  getInsight(creativeId) {
    return request(`/creatives/${creativeId}/insights`)
  },

  generateInsight(creativeId, { byok_key = null, byok_provider = null } = {}) {
    return request(`/creatives/${creativeId}/generate-insights`, {
      method: "POST",
      params: { byok_key, byok_provider },
    })
  },

  listInsights({ page = 1, page_size = 20 } = {}) {
    return request("/insights", { params: { page, page_size } })
  },

  generatePatterns({ byok_key = null, byok_provider = null } = {}) {
    return request("/patterns/generate", {
      method: "POST",
      params: { byok_key, byok_provider },
    })
  },
}

export default analysisService
