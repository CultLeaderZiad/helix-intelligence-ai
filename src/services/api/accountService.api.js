import { request, uploadFile } from "../http"

const accountService = {
  getProfile() {
    return request("/account/profile")
  },

  updateProfile(data) {
    return request("/account/profile", {
      method: "PATCH",
      body: data,
    })
  },

  uploadAvatar(file) {
    const formData = new FormData()
    formData.append("file", file)
    return uploadFile("/account/avatar", formData)
  },

  getTodayUsage() {
    return request("/account/usage/today")
  },

  completeOnboarding() {
    return request("/account/onboarding-complete", {
      method: "POST",
    })
  },

  getBilling() {
    return request("/account/billing")
  },

  getAccess() {
    return request("/account/access")
  },

  createAccessRequest(features, note, orgId) {
    return request("/account/access-requests", {
      method: "POST",
      body: { features, note, org_id: orgId || undefined },
    })
  },

  selectWorkspace(orgId) {
    return request("/account/workspace", {
      method: "POST",
      body: { org_id: orgId },
    })
  },

  listApiKeys() {
    return request("/account/api-keys")
  },

  createApiKey(name = "Default API Key") {
    return request("/account/api-keys", {
      method: "POST",
      body: { name },
    })
  },

  revokeApiKey(keyId) {
    return request(`/account/api-keys/${keyId}`, {
      method: "DELETE",
    })
  },

  getTeam() {
    return request("/account/team")
  },

  inviteTeamMember(email, role = "member") {
    return request("/account/team/invites", {
      method: "POST",
      body: { email, role },
    })
  },

  cancelTeamInvite(inviteId) {
    return request(`/account/team/invites/${inviteId}`, {
      method: "DELETE",
    })
  },

  removeTeamMember(memberId) {
    return request(`/account/team/members/${memberId}`, {
      method: "DELETE",
    })
  },

  acceptTeamInvite(token) {
    return request("/account/team/invites/accept", {
      method: "POST",
      body: { token },
    })
  },
}

export default accountService
