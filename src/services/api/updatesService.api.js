import { request } from "../http"

export const updatesApi = {
  /**
   * Fetch all published updates (active or scheduled)
   */
  async getPublishedUpdates() {
    return request("/updates")
  },

  /**
   * Fetch the single active public/app-wide banner
   */
  async getBanner() {
    return request("/updates/banner")
  },

  /**
   * Admin: List all updates
   */
  async getAdminUpdates() {
    return request("/updates/admin/all")
  },

  /**
   * Admin: Create a new update or banner
   */
  async createAdminUpdate(payload) {
    return request("/updates/admin", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  },

  /**
   * Admin: Get a single update by ID
   */
  async getAdminUpdate(id) {
    return request(`/updates/admin/${id}`)
  },

  /**
   * Admin: Update/toggle an update
   */
  async updateAdminUpdate(id, payload) {
    return request(`/updates/admin/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  },

  /**
   * Admin: Delete an update
   */
  async deleteAdminUpdate(id) {
    return request(`/updates/admin/${id}`, {
      method: "DELETE",
    })
  },
}

export default updatesApi
