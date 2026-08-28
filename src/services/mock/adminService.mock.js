import { ServiceError } from "../http"
import { delay, maybeFail } from "./latency"

/**
 * Mock admin service.
 *
 * Backs the operations console. Satisfies the same interface as
 * adminService.api.js so flipping VITE_DATA_SOURCE=api needs zero
 * page/hook changes.
 *
 * The figures below are a fixed fixture, not random per call: an
 * operations dashboard whose totals flicker on every poll is worse than
 * useless. Derived values (active job count, rolled-up health) are
 * computed from that fixture so the strip, the table, and the health
 * panel can never disagree with each other.
 */

/* ------------------------------------------------------------------ */
/* Fixture — stands in for cross-tenant tables the backend will own    */
/* ------------------------------------------------------------------ */

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const now = () => Date.now()
const isoAgo = (ms) => new Date(now() - ms).toISOString()

const ORGANIZATIONS_TOTAL = 42

/** Recent cross-tenant scrape jobs, newest first. */
const JOB_ROWS = [
  {
    job_id: "job_9fa21c",
    organization: "Northwind Labs",
    query: "meta skincare hooks",
    status: "running",
    records: 318,
    duration_ms: 41_000,
    created_at: isoAgo(3 * MINUTE),
  },
  {
    job_id: "job_9f8b04",
    organization: "Atlas Retail Group",
    query: "tiktok back-to-school",
    status: "running",
    records: 122,
    duration_ms: 18_500,
    created_at: isoAgo(6 * MINUTE),
  },
  {
    job_id: "job_9e77de",
    organization: "Vantage Fintech",
    query: "linkedin b2b saas demo",
    status: "queued",
    records: 0,
    duration_ms: 0,
    created_at: isoAgo(8 * MINUTE),
  },
  {
    job_id: "job_9e0a13",
    organization: "Northwind Labs",
    query: "youtube pre-roll retention",
    status: "succeeded",
    records: 1_204,
    duration_ms: 52_400,
    created_at: isoAgo(22 * MINUTE),
  },
  {
    job_id: "job_9dbf90",
    organization: "Meridian DTC",
    query: "meta carousel offers",
    status: "succeeded",
    records: 867,
    duration_ms: 47_100,
    created_at: isoAgo(41 * MINUTE),
  },
  {
    job_id: "job_9d51a7",
    organization: "Atlas Retail Group",
    query: "reddit community launch",
    status: "failed",
    records: 0,
    duration_ms: 12_900,
    created_at: isoAgo(58 * MINUTE),
  },
  {
    job_id: "job_9cf2e8",
    organization: "Vantage Fintech",
    query: "meta lead gen variants",
    status: "succeeded",
    records: 512,
    duration_ms: 38_700,
    created_at: isoAgo(75 * MINUTE),
  },
  {
    job_id: "job_9c8b11",
    organization: "Helios Mobility",
    query: "tiktok rider acquisition",
    status: "succeeded",
    records: 1_988,
    duration_ms: 61_300,
    created_at: isoAgo(2 * HOUR),
  },
]

/** Monitored dependencies. `status` maps directly to a design token. */
const SERVICE_HEALTH = [
  {
    id: "svc_ad_source",
    name: "Ad source API",
    status: "success",
    detail: "All sources responding",
    latency_ms: 214,
    last_checked: isoAgo(40_000),
  },
  {
    id: "svc_scrapegraph",
    name: "ScrapeGraphAI",
    status: "warning",
    detail: "Elevated queue depth",
    latency_ms: 892,
    last_checked: isoAgo(55_000),
  },
  {
    id: "svc_ai_router",
    name: "AI router",
    status: "success",
    detail: "Nominal",
    latency_ms: 331,
    last_checked: isoAgo(30_000),
  },
  {
    id: "svc_database",
    name: "Database",
    status: "success",
    detail: "Primary + replica healthy",
    latency_ms: 12,
    last_checked: isoAgo(20_000),
  },
]

/* ------------------------------------------------------------------ */
/* Derivations — one source of truth for figures shown in three places */
/* ------------------------------------------------------------------ */

const WORST_FIRST = { danger: 0, warning: 1, success: 2 }

/** Roll the per-service statuses up into a single platform state. */
function rollUpHealth(services) {
  const worst = services.reduce(
    (acc, s) => Math.min(acc, WORST_FIRST[s.status] ?? 2),
    2,
  )
  if (worst === 0) return "down"
  if (worst === 1) return "degraded"
  return "operational"
}

function countActiveJobs(rows) {
  return rows.filter((j) => j.status === "queued" || j.status === "running").length
}

/* ------------------------------------------------------------------ */
/* Public interface — must match adminService.api.js exactly           */
/* ------------------------------------------------------------------ */

const adminService = {
  /**
   * Headline counters for the overview strip.
   * @returns {Promise<import('../contracts').AdminOverviewStats>}
   */
  async getOverviewStats() {
    await delay(180)
    maybeFail("Admin metrics service unavailable")

    return {
      organizations: ORGANIZATIONS_TOTAL,
      active_scrape_jobs: countActiveJobs(JOB_ROWS),
      system_health: rollUpHealth(SERVICE_HEALTH),
      api_error_rate: 0.42,
      window_label: "trailing 24h",
    }
  },

  /**
   * Recent cross-tenant scrape jobs for the overview table.
   * @returns {Promise<import('../contracts').Paginated>}
   */
  async listRecentJobs() {
    await delay(220)
    maybeFail("Job index temporarily unavailable")

    const items = [...JOB_ROWS].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at),
    )
    return {
      items,
      total: items.length,
      page: 1,
      page_size: items.length,
      has_more: false,
    }
  },

  /**
   * Monitored dependency states plus the rolled-up platform state.
   * @returns {Promise<import('../contracts').AdminSystemHealth>}
   */
  async getSystemHealth() {
    await delay(160)
    maybeFail("Health probe service unavailable")

    const services = [...SERVICE_HEALTH]
    return { state: rollUpHealth(services), services }
  },

  async listPlans() {
    await delay(150)
    return [
      { id: "plan_trial_default", name: "7-Day Free Trial", type: "trial", credit_allowance: 25, daily_credit_limit: 3.5, price_per_credit: 0.0, feature_flags: { discover: true, intelligence: true, create: true, performance: true, swipe_files: true, team_accounts: false, public_api: false } },
      { id: "plan_payg_default", name: "Pay As You Go", type: "pay_as_you_go", credit_allowance: 0, daily_credit_limit: null, price_per_credit: 0.01, feature_flags: { discover: true, intelligence: true, create: true, performance: true, swipe_files: true, team_accounts: true, public_api: false } },
      { id: "plan_enterprise_custom", name: "Enterprise Custom", type: "custom", credit_allowance: 500, daily_credit_limit: null, price_per_credit: 0.008, feature_flags: { discover: true, intelligence: true, create: true, performance: true, swipe_files: true, team_accounts: true, public_api: true } },
    ]
  },

  async createPlan(planData) {
    await delay(150)
    return { id: `plan_${Date.now()}`, ...planData }
  },

  async listOrganizations() {
    await delay(150)
    return [
      { id: "org_1", name: "Acme Corp", owner_id: "user_1", owner_email: "acme@example.com", plan_id: "plan_trial_default", plan_name: "7-Day Free Trial", plan_type: "trial", credit_balance: 18.0, credits_used: 7.0, custom_feature_flags: {}, effective_feature_flags: { discover: true, intelligence: true, create: true }, status: "active", total_jobs: 4 },
      { id: "org_2", name: "Stripe Demo", owner_id: "user_2", owner_email: "demo@stripe.com", plan_id: "plan_payg_default", plan_name: "Pay As You Go", plan_type: "pay_as_you_go", credit_balance: 140.0, credits_used: 60.0, custom_feature_flags: {}, effective_feature_flags: { discover: true, intelligence: true, create: true, team_accounts: true }, status: "active", total_jobs: 12 },
    ]
  },

  async grantCredits(orgId, amount, reason) {
    await delay(150)
    return { success: true, message: `Granted ${amount} credits`, new_balance: 100.0, status: "active" }
  },

  async switchPlan(orgId, planId, resetCredits) {
    await delay(150)
    return { success: true, message: `Switched plan to ${planId}`, plan_id: planId, credit_balance: 50.0, status: "active" }
  },

  async updateFeatureFlags(orgId, featureFlags) {
    await delay(150)
    return { success: true, message: "Feature flags updated", custom_feature_flags: featureFlags }
  },

  async getUsageSummary() {
    await delay(150)
    return {
      total_cost_usd: 1.42,
      total_credits_deducted: 142.5,
      total_requests: 64,
      by_provider: [
        { provider: "brightdata", operation: "discover_scrape", total_units: 12.0, total_cost_usd: 0.036, total_credits_deducted: 12.0, total_requests: 12 },
        { provider: "scrapegraph", operation: "landing_enrich", total_units: 40.0, total_cost_usd: 0.20, total_credits_deducted: 20.0, total_requests: 12 },
        { provider: "groq", operation: "pattern_synthesis", total_units: 24000.0, total_cost_usd: 0.014, total_credits_deducted: 6.0, total_requests: 12 }
      ],
      recent_logs: []
    }
  },

  async listUsers() {
    await delay(150)
    return [
      { id: "user_1", email: "admin@helix.ai", role: "admin", created_at: new Date().toISOString(), status: "active" },
      { id: "user_2", email: "customer@example.com", role: "customer", created_at: new Date().toISOString(), status: "active" }
    ]
  },

  async impersonateUser(userId) {
    await delay(150)
    return { access_token: "mock-impersonated-token", token_type: "bearer", user_id: userId, email: "impersonated@example.com", role: "customer" }
  }
}

export default adminService
