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
const CACHED_USER_KEY = "helix_cached_user"

export function getStoredToken() {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY) || localStorage.getItem("helix_auth_token")
}

export function getCachedUser() {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(CACHED_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function storeUser(user) {
  if (typeof window === "undefined" || !user) return
  try {
    localStorage.setItem(CACHED_USER_KEY, JSON.stringify(user))
  } catch {}
}

function storeToken(token) {
  if (typeof window === "undefined") return
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem("helix_auth_token", token)
  }
}

function clearToken() {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem("helix_auth_token")
  localStorage.removeItem(CACHED_USER_KEY)
}

/**
 * Map a FastAPI SessionResponse into the AuthContext user shape.
 */
function sessionToUser(session, fallbackName) {
  if (!session) return null
  const emailLocal = session.email?.split("@")[0] ?? "user"
  const displayName = session.full_name || session.name || fallbackName || emailLocal
  return {
    id: session.user_id,
    email: session.email,
    role: session.role ?? "customer",
    name: displayName,
    full_name: session.full_name ?? null,
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
  getStoredToken,
  getCachedUser,

  /**
   * Resolve the persisted session from the stored Bearer token.
   * Uses Stale-While-Revalidate pattern so Render waking up never drops valid sessions.
   */
  async getSession() {
    const token = getStoredToken()
    if (!token) {
      clearToken()
      return null
    }

    try {
      const session = await request("/auth/session")
      const user = sessionToUser(session)
      if (user) {
        storeUser(user)
        return { user }
      }
      return null
    } catch (err) {
      // Only wipe session if credentials were actively rejected by the backend authority
      if (err?.status === 401 || err?.status === 403) {
        clearToken()
        return null
      }

      // If backend is sleeping (502/503/504) or network glitched, preserve cached user
      const cached = getCachedUser()
      if (cached) {
        return { user: cached }
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
    const user = sessionToUser(session)
    storeUser(user)
    return { user }
  },

  /**
   * Register a new account.
   * Stores the returned JWT and returns the user shape.
   */
  async signUp({ name, email, password } = {}) {
    const cleanName = name ? String(name).trim() : undefined
    const cleanEmail = String(email ?? "").trim().toLowerCase()

    const session = await request("/auth/sign-up", {
      method: "POST",
      body: {
        name: cleanName,
        email: cleanEmail,
        password,
      },
    })

    if (!session?.access_token) {
      throw new ServiceError("Sign-up succeeded but no access token returned", {
        code: "no_token",
      })
    }

    storeToken(session.access_token)
    const user = sessionToUser(session, cleanName)
    storeUser(user)
    return { user }
  },

  /**
   * Sign out — always clears local token and cached profile.
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
   * Start a password reset. Always resolves with the same generic shape
   * whether or not the account exists (no account enumeration). Returns
   * `reset_url` when the backend runs in dev-delivery mode (no mail
   * provider configured) so the UI can surface it.
   */
  async requestPasswordReset({ email } = {}) {
    const payload = await request("/auth/forgot-password", {
      method: "POST",
      body: { email: String(email ?? "").trim().toLowerCase() },
    })
    return { ok: true, reset_url: payload?.reset_url ?? null }
  },

  /**
   * Redeem a reset token with a new password. The backend returns a fresh
   * session, so a successful reset signs the user straight in.
   */
  async resetPassword({ token, newPassword } = {}) {
    const session = await request("/auth/reset-password", {
      method: "POST",
      body: { token: String(token ?? ""), new_password: newPassword },
    })
    if (!session?.access_token) {
      throw new ServiceError("Password reset succeeded but no session was returned", {
        code: "no_token",
      })
    }
    storeToken(session.access_token)
    return { user: sessionToUser(session) }
  },

  /**
   * Mark onboarding as complete on the server.
   */
  completeOnboarding() {
    return request("/auth/session/onboarding/complete", { method: "POST" })
  },
}

export default authService

