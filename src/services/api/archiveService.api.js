import { request } from "../http"

/** The workspace's permanent ad archive (text + re-hosted media). */
const archiveService = {
  /** @param {{page?: number, page_size?: number, brand?: string}} [params] */
  list(params = {}) {
    return request("/archive", { params })
  },

  /**
   * Full-text search (EN + AR) over the archive and saved ads. 0 records.
   * @param {string} q
   * @param {{scope?: "all"|"archive"|"saved", page?: number, page_size?: number}} [params]
   */
  search(q, params = {}) {
    return request("/archive/search", { params: { q, ...params } })
  },

  /** @param {string} creativeId */
  forCreative(creativeId) {
    return request(`/archive/by-creative/${encodeURIComponent(creativeId)}`)
  },
}

export default archiveService
