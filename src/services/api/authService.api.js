import { request, ServiceError } from "../http"

/**
 * FastAPI-backed auth service.
 *
 * The backend returns a flat SessionResponse:
 *   { user_id, email, role, access_token, token_type }
 *
 * AuthContext expects { user: { id, email, role } } from signIn/signUp,
 * and { user: {...} } or null from getSession.
 *
 * This service normalises the shape here so nothing else changes.
 */

const TOKEN_KEY = "helix_access_token"

function storeToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/** Shape a flat SessionResponse into { user } */
function toSession(data) {
  if (!data) return null
  return {
    user: {
      id: data.user_id,
      email: data.email,
      role: data.role,
      credit_balance: data.credit_balance,
      plan_id: data.plan_id,
      feature_flags: data.feature_flags || { discover: true, swipe_files: true },
    },
  }
}

const authService = {
  async getSession() {
    // Try the token we have in storage — if none, return null immediately
    const token = getStoredToken()
    if (!token) return null
    try {
      const data = await request("/auth/session", {
        headers: { Authorization: `Bearer ${token}` },
      })
      return toSession(data)
    } catch (err) {
      if (err instanceof ServiceError && err.status === 401) {
        clearToken()
        return null
      }
      throw err
    }
  },

  async signIn({ email, password } = {}) {
    const data = await request("/auth/sign-in", {
      method: "POST",
      body: { email, password },
    })
    storeToken(data.access_token)
    return toSession(data)
  },

  async signUp({ name, email, password } = {}) {
    const data = await request("/auth/sign-up", {
      method: "POST",
      body: { name, email, password },
    })
    storeToken(data.access_token)
    return toSession(data)
  },

  signOut() {
    clearToken()
    return request("/auth/sign-out", { method: "POST" }).catch(() => null)
  },

  requestPasswordReset({ email } = {}) {
    return request("/auth/password-reset", { method: "POST", body: { email } })
  },
}

export default authService
