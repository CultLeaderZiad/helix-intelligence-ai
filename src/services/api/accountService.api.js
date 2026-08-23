import { request } from "../http"

const accountService = {
  getBilling() {
    return request("/account/billing")
  },

  listApiKeys() {
    return request("/account/api-keys")
  },

  createApiKey(name = "Default API Key") {
    return request("/account/api-keys", {
      method: "POST",
      body: JSON.stringify({ name }),
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
      body: JSON.stringify({ email, role }),
    })
  },

  cancelTeamInvite(inviteId) {
    return request(`/account/team/invites/${inviteId}`, {
      method: "DELETE",
    })
  },

  acceptTeamInvite(token) {
    return request("/account/team/invites/accept", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
  },
}

export default accountService
