import { request, ServiceError } from "../http"

/**
 * FastAPI-backed auth service.
 *
 * Written up front and intentionally thin. Because it satisfies the same
 * interface as authService.mock.js, switching VITE_DATA_SOURCE=api needs
 * zero context/page changes.
 *
 * Sessions are cookie-based server-side: the browser sends the httpOnly
 * session cookie automatically, so there is no token to store or attach
 * here. `credentials: 'include'` is handled in the shared request() layer
 * when the app cuts over.
 *
 * Expected endpoints:
 *   POST /v1/auth/sign-in         -> { user }
 *   POST /v1/auth/sign-up         -> { user }
 *   POST /v1/auth/sign-out        -> 204
 *   POST /v1/auth/password-reset  -> { ok, email }
 *   GET  /v1/auth/session         -> { user }  (401 when unauthenticated)
 */
const authService = {
  async getSession() {
    try {
      return await request("/auth/session")
    } catch (err) {
      // "Not signed in" is a normal state, not an error to surface.
      if (err instanceof ServiceError && err.status === 401) return null
      throw err
    }
  },

  signIn({ email, password } = {}) {
    return request("/auth/sign-in", { method: "POST", body: { email, password } })
  },

  signUp({ name, email, password } = {}) {
    return request("/auth/sign-up", {
      method: "POST",
      body: { name, email, password },
    })
  },

  signOut() {
    return request("/auth/sign-out", { method: "POST" })
  },

  requestPasswordReset({ email } = {}) {
    return request("/auth/password-reset", { method: "POST", body: { email } })
  },
}

export default authService
