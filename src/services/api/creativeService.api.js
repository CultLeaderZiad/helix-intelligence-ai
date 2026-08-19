import { request } from "../http"

/**
 * Expected endpoints:
 *   GET /v1/creatives            -> Paginated<Creative>
 *   GET /v1/creatives/{id}       -> Creative (relations hydrated)
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

  getBrands() {
    return request("/brands")
  },

  getPatterns() {
    return request("/patterns")
  },
}

export default creativeService
