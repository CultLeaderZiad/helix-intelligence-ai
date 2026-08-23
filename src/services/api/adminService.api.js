import { request } from "../http"

/**
 * Real FastAPI-backed admin service for full platform control,
 * plans management, organization billing, credit grants, usage breakdown,
 * feature flags, and user impersonation.
 */
const adminService = {
  getOverviewStats() {
    return request("/admin/overview/stats")
  },

  async listRecentJobs() {
    const items = await request("/admin/jobs", { params: { page: 1, page_size: 20 } })
    return {
      items: Array.isArray(items) ? items : [],
      total: Array.isArray(items) ? items.length : 0,
      page: 1,
      page_size: 20,
      has_more: false,
    }
  },

  getSystemHealth() {
    return request("/admin/system/health")
  },

  // Plans Management
  listPlans() {
    return request("/admin/plans")
  },

  createPlan(planData) {
    return request("/admin/plans", {
      method: "POST",
      body: JSON.stringify(planData),
    })
  },

  // Organizations & Credits
  listOrganizations() {
    return request("/admin/organizations")
  },

  grantCredits(orgId, amount, reason = "Admin manual grant") {
    return request(`/admin/organizations/${orgId}/grant-credits`, {
      method: "POST",
      body: JSON.stringify({ amount, reason }),
    })
  },

  switchPlan(orgId, planId, resetCredits = false) {
    return request(`/admin/organizations/${orgId}/switch-plan`, {
      method: "POST",
      body: JSON.stringify({ plan_id: planId, reset_credits: resetCredits }),
    })
  },

  updateFeatureFlags(orgId, featureFlags) {
    return request(`/admin/organizations/${orgId}/feature-flags`, {
      method: "POST",
      body: JSON.stringify({ feature_flags: featureFlags }),
    })
  },

  // Usage & Provider Breakdown
  getUsageSummary() {
    return request("/admin/usage")
  },

  // Users & Impersonation
  listUsers() {
    return request("/admin/users")
  },

  impersonateUser(userId) {
    return request(`/admin/users/${userId}/impersonate`, {
      method: "POST",
    })
  },
}

export default adminService
