import { request } from "../http"

/**
 * Expected endpoints:
 *   GET /v1/creatives            -> Paginated<Creative>
 *   GET /v1/creatives/{id}       -> Creative (relations hydrated)
 *   GET /v1/creatives/saved      -> Paginated<Creative> (Swipe files)
 *   POST /v1/creatives/{id}/save -> Save to collection (0 credits)
 *   DELETE /v1/creatives/{id}/save -> Remove from swipe file
 *   POST /v1/creatives/custom    -> Add manual ad reference / URL to swipe file
 *   GET /v1/brands               -> Paginated<Brand>
 *   GET /v1/patterns             -> Paginated<Pattern>
 */
const creativeService = {
  getCreatives({ page = 1, page_size = 20, brand_id = null } = {}) {
    return request("/creatives", { params: { page, page_size, brand_id } })
  },

  getCreativeById(id) {
    return request(`/creatives/${id}`)
  },

  getSavedCreatives({ page = 1, page_size = 50, collection = null } = {}) {
    return request("/creatives/saved", { params: { page, page_size, collection } })
  },

  saveCreative(creativeId, collection = "Default") {
    return request(`/creatives/${creativeId}/save`, {
      method: "POST",
      params: { collection },
    })
  },

  async saveBulkCreatives(creativeIds = [], collection = "Default") {
    const results = []
    for (const id of creativeIds) {
      try {
        const res = await this.saveCreative(id, collection)
        results.push(res)
      } catch (err) {
        console.warn(`Failed to save creative ${id}`, err)
      }
    }
    return { success: true, count: results.length }
  },

  addCustomSwipeItem(data) {
    return request("/creatives/custom", {
      method: "POST",
      body: JSON.stringify(data),
    })
  },

  unsaveCreative(creativeId) {
    return request(`/creatives/${creativeId}/save`, {
      method: "DELETE",
    })
  },

  getBrands() {
    return request("/brands")
  },

  getPatterns() {
    return request("/patterns")
  },
}

export default creativeService
