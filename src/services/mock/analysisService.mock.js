import { insights, insightsByCreativeId } from "@/data/insights"
import { delay, maybeFail } from "./latency"

/**
 * Mock analysis service.
 *
 * Insight generation will be model-backed and slow, so latency here is
 * deliberately higher than the read services. Insights carry provenance
 * and confidence, never a bare string, so the UI must attribute claims.
 */
const analysisService = {
  /**
   * @param {string} creativeId
   * @returns {Promise<import('../contracts').Paginated>}
   */
  async getInsight(creativeId) {
    await delay(650)
    maybeFail("Analysis worker did not respond in time")

    const items = insightsByCreativeId[creativeId] ?? []
    return {
      items,
      total: items.length,
      page: 1,
      page_size: items.length,
      has_more: false,
    }
  },

  /** Cross-corpus insights for the Intelligence surface. */
  async listInsights({ page = 1, page_size = 20 } = {}) {
    await delay(420)
    const total = insights.length
    const start = (page - 1) * page_size
    return {
      items: insights.slice(start, start + page_size),
      total,
      page,
      page_size,
      has_more: start + page_size < total,
    }
  },
}

export default analysisService
