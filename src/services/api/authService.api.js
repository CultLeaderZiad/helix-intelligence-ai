import { request, ServiceError } from "../http"
import { API_BASE_URL } from "../config"
import { withColdStartRetry } from "../coldStart"
import {
  clearSession,
  getAccessToken,
  getCachedUser as readCachedUser,
  setAccessToken,
  setCachedUser,
} from "../sessionStore"

let sessionOperationVersion = 0

function beginSessionOperation() {
  sessionOperationVersion += 1
  return sessionOperationVersion
}

function assertCurrentSessionOperation(version) {
  if (version !== sessionOperationVersion) {
    throw new ServiceError("Session changed while authentication was in progress", {
      code: "session_changed",
    })
  }
}

/** @type {Map<string, Promise<unknown>>} */
const authFlights = new Map()

/**
 * One in-flight auth submit per key. A second caller joins the same promise
 * instead of starting another POST.
 * @template T
 * @param {string} key
 * @param {() => Promise<T>} run
 * @returns {Promise<T>}
 */
function shareInFlight(key, run) {
  const existing = authFlights.get(key)
  if (existing) return /** @type {Promise<T>} */ (existing)
  const promise = Promise.resolve().then(run).finally(() => {
    if (authFlights.get(key) === promise) authFlights.delete(key)
  })
  authFlights.set(key, promise)
  return promise
}

/** Test seam: drop joined auth submits between cases. */
export function resetAuthFlights() {
  authFlights.clear()
}

/** @type {import("../coldStart").ColdStartOptions} */
let recoveryOverrides = {}

/** Test seam: replace the health-wait clock without waiting on real time.
 * @param {import("../coldStart").ColdStartOptions} [options]
 */
export function setAuthRecoveryOverridesForTests(options = {}) {
  recoveryOverrides = options
}

/**
 * Auth writes are not idempotent, so the HTTP client does not retry them.
 * A cold Render instance instead fails the attempt, we wait for /api/health,
 * and then the same write runs once more.
 * @template T
 * @param {() => Promise<T>} operation
 * @returns {Promise<T>}
 */
function recoverAuthRequest(operation) {
  return withColdStartRetry(operation, {
    healthUrl: `${API_BASE_URL}/health`,
    createUnavailableError() {
      return new ServiceError("The server is unavailable. Try again in a moment.", {
        code: "server_unavailable",
      })
    },
    ...recoveryOverrides,
  })
}

/**
 * FastAPI-backed auth service.
 *
 * All auth goes to the Helix FastAPI backend (Render).
 * Zero dependency on better-auth / Neon Auth / VITE_NEON_AUTH_URL.
 */

export function getStoredToken() {
  return getAccessToken()
}

export function getCachedUser() {
  return readCachedUser()
}

function storeUser(user) {
  setCachedUser(user)
}

function storeToken(token) {
  setAccessToken(token)
}

export function clearAllTenantStorage() {
  notifySessionClearing()
  clearSession()
}

function notifySessionClearing() {
  if (typeof window === "undefined") return
  try {
    window.dispatchEvent(new Event("helix:session-clearing"))
  } catch {
    // Session cleanup must still proceed if event dispatch is unavailable.
  }
}

function storeSession(token, user) {
  clearAllTenantStorage()
  if (user) storeUser(user)
  storeToken(token)
}

function clearToken() {
  clearAllTenantStorage()
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
    organization_id: session.organization_id ?? session.org_id ?? null,
    role: session.role ?? "customer",
    name: displayName,
    full_name: session.full_name ?? null,
    credit_balance: session.credit_balance ?? 0,
    daily_credit_limit: session.daily_credit_limit ?? null,
    daily_credits_used: session.daily_credits_used ?? 0,
    daily_credits_remaining: session.daily_credits_remaining ?? null,
    daily_credits_resets_at_utc: session.daily_credits_resets_at_utc ?? null,
    plan_id: session.plan_id ?? null,
    has_completed_onboarding: session.has_completed_onboarding ?? false,
    feature_flags: session.feature_flags ?? {},
    access_status: session.access_status ?? null,
    access_expires_at: session.access_expires_at ?? null,
    is_platform_admin: session.is_platform_admin ?? false,
  }
}

/** @param {{ email?: string, password?: string }} [credentials] */
async function performSignIn({ email, password } = {}) {
  const operationVersion = beginSessionOperation()
  const session = await recoverAuthRequest(() => request("/auth/sign-in", {
    method: "POST",
    body: { email: String(email ?? "").trim().toLowerCase(), password },
  }))

  if (!session?.access_token) {
    throw new ServiceError("Sign-in succeeded but no access token returned", {
      code: "no_token",
    })
  }
  assertCurrentSessionOperation(operationVersion)

  const user = sessionToUser(session)
  storeSession(session.access_token, user)
  return { user }
}

/** @param {{ name?: string, email?: string, password?: string, utm_source?: string, utm_medium?: string, utm_campaign?: string, utm_term?: string, utm_content?: string, referrer?: string }} [params] */
async function performSignUp({ name, email, password, utm_source, utm_medium, utm_campaign, utm_term, utm_content, referrer } = {}) {
  const operationVersion = beginSessionOperation()
  const cleanName = name ? String(name).trim() : undefined
  const cleanEmail = String(email ?? "").trim().toLowerCase()

  await recoverAuthRequest(() => request("/auth/sign-up", {
    method: "POST",
    body: {
      name: cleanName,
      email: cleanEmail,
      password,
      utm_source,
      utm_medium,
      utm_campaign,
      utm_term,
      utm_content,
      referrer,
    },
  }))
  assertCurrentSessionOperation(operationVersion)

  const session = await recoverAuthRequest(() => request("/auth/sign-in", {
    method: "POST",
    body: { email: cleanEmail, password },
  }))

  if (!session?.access_token) {
    throw new ServiceError("Sign-in succeeded but no access token returned", {
      code: "no_token",
    })
  }
  assertCurrentSessionOperation(operationVersion)

  const user = sessionToUser(session, cleanName)
  storeSession(session.access_token, user)
  return { user }
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
    const operationVersion = sessionOperationVersion

    try {
      const session = await request("/auth/session")
      if (getStoredToken() !== token || operationVersion !== sessionOperationVersion) return null
      const user = sessionToUser(session)
      if (user) {
        storeUser(user)
        return { user }
      }
      return null
    } catch (err) {
      // Only wipe session if credentials were actively rejected by the backend authority
      if (
        (err?.status === 401 || err?.status === 403) &&
        getStoredToken() === token &&
        operationVersion === sessionOperationVersion
      ) {
        clearToken()
        return null
      }

      if (getStoredToken() !== token || operationVersion !== sessionOperationVersion) return null

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
  /** @param {{ email?: string, password?: string }} [credentials] */
  signIn(credentials) {
    return shareInFlight("auth:sign-in", () => performSignIn(credentials))
  },

  /**
   * Register a new account, then sign in with the same credentials.
   *
   * The server answers sign-up identically whether or not the email was
   * already registered (no token, same body), so the session comes from the
   * sign-in that follows. An existing account with a different password
   * therefore surfaces as the usual generic sign-in error.
   */
  /** @param {{ name?: string, email?: string, password?: string, utm_source?: string, utm_medium?: string, utm_campaign?: string, utm_term?: string, utm_content?: string, referrer?: string }} [params] */
  signUp(params) {
    return shareInFlight("auth:sign-up", () => performSignUp(params))
  },

  /**
   * Sign out — always clears local token and cached profile.
   */
  async signOut() {
    const operationVersion = beginSessionOperation()
    const token = getStoredToken()
    notifySessionClearing()
    try {
      await request("/auth/sign-out", { method: "POST" })
    } catch {
      // Ignore server errors; local token must be cleared either way.
    } finally {
      if (operationVersion === sessionOperationVersion && getStoredToken() === token) clearToken()
    }
    return null
  },


  /**
   * Start a password reset. Always resolves with the same generic shape
   * whether or not the account exists (no account enumeration). Returns
   * The backend does not return a reset URL. Delivery is email-only.
   */
  /** @param {{ email?: string }} [params] */
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
  /** @param {{ token?: string, newPassword?: string }} [params] */
  async resetPassword({ token, newPassword } = {}) {
    const operationVersion = beginSessionOperation()
    const session = await request("/auth/reset-password", {
      method: "POST",
      body: { token: String(token ?? ""), new_password: newPassword },
    })
    if (!session?.access_token) {
      throw new ServiceError("Password reset succeeded but no session was returned", {
        code: "no_token",
      })
    }
    assertCurrentSessionOperation(operationVersion)
    const user = sessionToUser(session)
    storeSession(session.access_token, user)
    return { user }
  },

  /** @param {string} token */
  switchToImpersonatedSession(token) {
    beginSessionOperation()
    if (!token) {
      throw new ServiceError("Impersonation did not return an access token", {
        code: "no_token",
      })
    }
    clearAllTenantStorage()
    storeToken(token)
  },

  /**
   * Mark onboarding as complete on the server.
   */
  completeOnboarding() {
    return request("/auth/session/onboarding/complete", { method: "POST" })
  },

  /** Reset the server-side onboarding flag so the user can replay the tour. */
  restartOnboarding() {
    return request("/auth/session/onboarding/restart", { method: "POST" })
  },
}

export default authService

