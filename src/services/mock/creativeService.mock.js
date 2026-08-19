import { creatives } from "@/data/creatives"
import { brands, brandsById } from "@/data/brands"
import { patterns, patternsById } from "@/data/patterns"
import { ServiceError } from "../http"
import { delay, maybeFail } from "./latency"

/**
 * Mock creative service — direct reads that are NOT worker-backed and so
 * resolve synchronously-ish (still promise-based, still latent).
 */
const creativeService = {
  /**
   * Browse creatives without running a discovery job.
   * @returns {Promise<import('../contracts').Paginated>}
   */
  async getCreatives({ page = 1, page_size = 20, brand_id = null } = {}) {
    await delay()
    maybeFail()

    const filtered = brand_id
      ? creatives.filter((c) => c.brand_id === brand_id)
      : creatives

    const total = filtered.length
    const start = (page - 1) * page_size

    return {
      items: filtered.slice(start, start + page_size),
      total,
      page,
      page_size,
      has_more: start + page_size < total,
    }
  },

  /**
   * @param {string} id
   * @returns {Promise<import('../contracts').Creative & { brand: any, patterns: any[] }>}
   */
  async getCreativeById(id) {
    await delay(200)
    const found = creatives.find((c) => c.id === id)
    if (!found) {
      throw new ServiceError(`Creative ${id} not found`, {
        status: 404,
        code: "creative_not_found",
      })
    }
    // The detail endpoint hydrates relations; the list endpoint does not.
    return {
      ...found,
      brand: brandsById[found.brand_id] ?? null,
      patterns: (found.pattern_ids ?? [])
        .map((pid) => patternsById[pid])
        .filter(Boolean),
    }
  },

  async getBrands() {
    await delay(160)
    return {
      items: brands,
      total: brands.length,
      page: 1,
      page_size: brands.length,
      has_more: false,
    }
  },

  async getPatterns() {
    await delay(160)
    return {
      items: patterns,
      total: patterns.length,
      page: 1,
      page_size: patterns.length,
      has_more: false,
    }
  },
}

export default creativeService
