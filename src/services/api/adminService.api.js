import { request } from "../http"

/**
 * Real FastAPI-backed admin service for full platform control,
 * plans management, organization billing, credit grants, usage breakdown,
 * feature flags, user management, announcements, and support tickets.
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

  // --- Plans Management ---
  listPlans() {
    return request("/admin/plans")
  },

  createPlan(planData) {
    return request("/admin/plans", {
      method: "POST",
      body: planData,
    })
  },

  updatePlan(planId, planData) {
    return request(`/admin/plans/${planId}`, {
      method: "PUT",
      body: planData,
    })
  },

  // --- Organizations & Credits ---
  listOrganizations() {
    return request("/admin/organizations")
  },

  grantCredits(orgId, amount, reason = "Admin manual grant") {
    return request(`/admin/organizations/${orgId}/grant-credits`, {
      method: "POST",
      body: { amount, reason },
    })
  },

  switchPlan(orgId, planId, resetCredits = false) {
    return request(`/admin/organizations/${orgId}/switch-plan`, {
      method: "POST",
      body: { plan_id: planId, reset_credits: resetCredits },
    })
  },

  updateFeatureFlags(orgId, featureFlags) {
    return request(`/admin/organizations/${orgId}/feature-flags`, {
      method: "POST",
      body: { feature_flags: featureFlags },
    })
  },

  // --- Usage & Provider Breakdown ---
  getUsageSummary() {
    return request("/admin/usage")
  },

  getUsageLogsFiltered(params = {}) {
    return request("/admin/usage/logs", { params })
  },

  // --- Users & Impersonation & Roles ---
  listUsers() {
    return request("/admin/users")
  },

  updateUserStatus(userId, status) {
    return request(`/admin/users/${userId}/status`, {
      method: "POST",
      body: { status },
    })
  },

  banUser(userId, isBanned) {
    return request(`/admin/users/${userId}/ban`, {
      method: "POST",
      body: { is_banned: isBanned },
    })
  },

  updateUserRole(userId, role, adminPermissions = {}) {
    return request(`/admin/users/${userId}/role`, {
      method: "POST",
      body: { role, admin_permissions: adminPermissions },
    })
  },

  switchUserPlan(userId, planId) {
    return request(`/admin/users/${userId}/plan`, {
      method: "POST",
      body: { plan_id: planId },
    })
  },

  impersonateUser(userId) {
    return request(`/admin/users/${userId}/impersonate`, {
      method: "POST",
    })
  },

  // --- Admin Broadcast Announcements ---
  broadcastAnnouncement(title, message, type = "system", link = null) {
    return request("/admin/broadcast", {
      method: "POST",
      body: { title, message, type, link },
    })
  },

  // --- Admin Support & Feedback Hub ---
  listSupportTickets(status = null, type = null) {
    const params = {}
    if (status && status !== "all") params.status = status
    if (type && type !== "all") params.type = type
    return request("/admin/support/tickets", { params })
  },

  replySupportTicket(ticketId, message) {
    return request(`/admin/support/tickets/${ticketId}/reply`, {
      method: "POST",
      body: { message },
    })
  },

  updateSupportTicketStatus(ticketId, status) {
    return request(`/admin/support/tickets/${ticketId}/status`, {
      method: "PATCH",
      body: { status },
    })
  },
}

export default adminService
