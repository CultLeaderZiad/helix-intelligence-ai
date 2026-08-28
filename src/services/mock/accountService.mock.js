import { delay } from "./latency"

const accountService = {
  async getBilling() {
    await delay(150)
    return {
      org_id: "org_mock",
      org_name: "Customer Workspace",
      plan_id: "plan_trial_default",
      plan_name: "7-Day Free Trial",
      plan_type: "trial",
      credit_balance: 21.0,
      credits_used: 4.0,
      status: "active",
      trial_expires_at: new Date(Date.now() + 5 * 86400000).toISOString(),
      trial_days_remaining: 5,
      feature_flags: { discover: true, swipe_files: true, team_accounts: false, public_api: false },
      recent_usage: [
        { id: "u_1", provider: "groq", operation: "pattern_synthesis", units: 1800, credits_deducted: 0.5, cost_usd: 0.001, created_at: new Date().toISOString() },
        { id: "u_2", provider: "brightdata", operation: "discover_scrape", units: 12, credits_deducted: 1.0, cost_usd: 0.003, created_at: new Date().toISOString() }
      ]
    }
  },

  async listApiKeys() {
    await delay(150)
    return [
      { id: "k_1", name: "Default API Key", prefix: "hlx_live_a89e...", is_active: true, created_at: new Date().toISOString(), last_used_at: null }
    ]
  },

  async createApiKey(name = "Default API Key") {
    await delay(150)
    return { id: "k_2", name, prefix: "hlx_live_b90f...", api_key: "hlx_live_b90f1234567890abcdef1234567890abcdef", created_at: new Date().toISOString() }
  },

  async revokeApiKey(keyId) {
    await delay(100)
    return { success: true, message: "API key revoked" }
  },

  async getTeam() {
    await delay(150)
    return {
      org_id: "org_mock",
      org_name: "Customer Workspace",
      members: [
        { id: "m_1", user_id: "u_1", email: "customer@example.com", role: "owner", joined_at: new Date().toISOString() }
      ],
      invites: []
    }
  },

  async inviteTeamMember(email, role = "member") {
    await delay(150)
    return { success: true, message: `Invite sent to ${email}`, invite_id: "inv_1", token: "tok_123" }
  },

  async cancelTeamInvite(inviteId) {
    await delay(100)
    return { success: true, message: "Invite canceled" }
  },

  async acceptTeamInvite(token) {
    await delay(100)
    return { success: true, message: "Joined organization" }
  }
}

export default accountService
