import { request, ServiceError } from "../http"

/**
 * FastAPI-backed auth service.
 *
 * All auth goes to the Helix FastAPI backend (Render).
 * Zero dependency on better-auth / Neon Auth / VITE_NEON_AUTH_URL.
 *
 * Interface is identical to authService.mock.js so AuthContext and
 * every page works unchanged regardless of VITE_DATA_SOURCE.
 */

const TOKEN_KEY = "helix_access_token"

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

function storeToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * Map a FastAPI SessionResponse into the AuthContext user shape.
 *
 * SessionResponse fields from backend:
 *   user_id, email, role, access_token, feature_flags,
 *   credit_balance, trial_days_remaining, daily_credit_limit,
 *   daily_credits_used, daily_credits_remaining,
 *   daily_credits_resets_at_utc, plan_id, has_completed_onboarding
 *
 * AuthContext expects user.id (not user.user_id).
 */
function sessionToUser(session, fallbackName) {
  if (!session) return null
  const emailLocal = session.email?.split("@")[0] ?? "user"
  return {
    id: session.user_id,
    email: session.email,
    role: session.role ?? "customer",
    name: fallbackName ?? emailLocal,
    credit_balance: session.credit_balance ?? 0,
    trial_days_remaining: session.trial_days_remaining ?? null,
    daily_credit_limit: session.daily_credit_limit ?? null,
    daily_credits_used: session.daily_credits_used ?? 0,
    daily_credits_remaining: session.daily_credits_remaining ?? null,
    daily_credits_resets_at_utc: session.daily_credits_resets_at_utc ?? null,
    plan_id: session.plan_id ?? null,
    has_completed_onboarding: session.has_completed_onboarding ?? false,
    feature_flags: session.feature_flags ?? {},
  }
}

const authService = {
  /**
   * Resolve the persisted session from the stored Bearer token.
   * Returns null (not throws) when unauthenticated — that is normal.
   * Retries once automatically after 2.5s on network error (free tier cold start).
   */
  async getSession(isRetry = false) {
    const token = getStoredToken()
    if (!token) return null

    try {
      const session = await request("/auth/session")
      return { user: sessionToUser(session) }
    } catch (err) {
      if (err?.status === 401 || err?.status === 403) {
        clearToken()
        return null
      }
      // Retry once automatically on network error / gateway timeout during cold start
      if (!isRetry && (err?.code === "network_error" || [502, 503, 504].includes(err?.status))) {
        await new Promise((resolve) => setTimeout(resolve, 2500))
        return this.getSession(true)
      }
      return null
    }
  },

  /**
   * Sign in with email + password.
   * Stores the returned JWT and returns the user shape.
   */
  async signIn({ email, password } = {}) {
    const session = await request("/auth/sign-in", {
      method: "POST",
      body: { email: String(email ?? "").trim().toLowerCase(), password },
    })

    if (!session?.access_token) {
      throw new ServiceError("Sign-in succeeded but no access token returned", {
        code: "no_token",
      })
    }

    storeToken(session.access_token)
    return { user: sessionToUser(session) }
  },

  /**
   * Register a new account.
   * Stores the returned JWT and returns the user shape.
   */
  async signUp({ name, email, password } = {}) {
    const session = await request("/auth/sign-up", {
      method: "POST",
      body: {
        name: name ? String(name).trim() : undefined,
        email: String(email ?? "").trim().toLowerCase(),
        password,
      },
    })

    if (!session?.access_token) {
      throw new ServiceError("Sign-up succeeded but no access token returned", {
        code: "no_token",
      })
    }

    storeToken(session.access_token)
    return { user: sessionToUser(session, name) }
  },

  /**
   * Sign out — always clears the local token regardless of server response.
   */
  async signOut() {
    try {
      await request("/auth/sign-out", { method: "POST" })
    } catch {
      // Ignore server errors; local token must be cleared either way.
    } finally {
      clearToken()
    }
    return null
  },

  /**
   * Password reset stub — no Neon Auth dependency.
   * Backend endpoint not yet implemented; returns ok immediately.
   */
  async requestPasswordReset({ email } = {}) {
    return { ok: true, email: String(email ?? "").trim().toLowerCase() }
  },

  /**
   * Mark onboarding as complete on the server.
   */
  completeOnboarding() {
    return request("/auth/session/onboarding/complete", { method: "POST" })
  },
}

export default authService

