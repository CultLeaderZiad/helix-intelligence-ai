import { request } from "../http"

/**
 * FastAPI-backed admin service.
 *
 * Written up front and intentionally thin. Because it satisfies the same
 * interface as adminService.mock.js, switching VITE_DATA_SOURCE=api needs
 * zero page or hook changes.
 *
 * These endpoints are admin-scoped server-side: the session cookie's role
 * claim gates them, so a customer session receives 403 here regardless of
 * what the client renders. The route guard is defense-in-depth, not the
 * authorization boundary.
 *
 * Expected endpoints:
 *   GET /v1/admin/overview/stats  -> AdminOverviewStats
 *   GET /v1/admin/jobs            -> Paginated<AdminJobRow>
 *   GET /v1/admin/system/health   -> AdminSystemHealth
 */
const adminService = {
  getOverviewStats() {
    return request("/admin/overview/stats")
  },

  listRecentJobs() {
    return request("/admin/jobs", { params: { page: 1, page_size: 8 } })
  },

  getSystemHealth() {
    return request("/admin/system/health")
  },
}

export default adminService
