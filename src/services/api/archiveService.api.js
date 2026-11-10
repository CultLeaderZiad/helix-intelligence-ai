import { request } from "../http"

/** The workspace's permanent ad archive (text + re-hosted media). */
const archiveService = {
  /** @param {{page?: number, page_size?: number, brand?: string}} [params] */
  list(params = {}) {
    return request("/archive", { params })
  },

  /** @param {string} creativeId */
  forCreative(creativeId) {
    return request(`/archive/by-creative/${encodeURIComponent(creativeId)}`)
  },
}

export default archiveService
