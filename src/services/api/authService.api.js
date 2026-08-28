import { createAuthClient } from "better-auth/react"
import { request, ServiceError } from "../http"

/**
 * Neon Auth (Better Auth) backed auth service.
 */

const TOKEN_KEY = "helix_access_token"

export const authClient = createAuthClient({
  // Point to the Neon Auth URL via environment variable
  baseURL: import.meta.env.VITE_NEON_AUTH_URL || "https://ep-fancy-bread-axe99xvb.neonauth.c-4.us-east-2.aws.neon.tech/neondb/auth"
})

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

function storeToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/** Shape a Better Auth User into our legacy session shape */
function toSession(user) {
  if (!user) return null
  return {
    user: {
      id: user.id,
      email: user.email,
      role: user.role || "user",
      name: user.name,
      // For now, mock the business fields until we fetch them from our own DB
      credit_balance: 0,
      trial_days_remaining: 0,
      daily_credit_limit: 10,
      daily_credits_used: 0,
      daily_credits_remaining: 10,
      has_completed_onboarding: true,
      feature_flags: { discover: true, swipe_files: true },
    },
  }
}

const authService = {
  async getSession() {
    try {
      const { data, error } = await authClient.getSession()
      if (error || !data?.user) {
        clearToken()
        return null
      }
      
      // Fetch extended user data from our own API using the access token
      try {
        const response = await request("/auth/session")
        return { user: { ...data.user, ...response } }
      } catch (backendError) {
        // Fallback if backend session fails
        return toSession(data.user)
      }
    } catch (err) {
      clearToken()
      return null
    }
  },

  async signIn({ email, password } = {}) {
    const { data, error } = await authClient.signIn.email({ email, password })
    if (error) throw new ServiceError(error.message, error.status)
    
    // Better Auth normally uses cookies, but for cross-domain API calls, we need a token.
    // If the token is returned in data.session.token, store it.
    if (data?.session?.token) {
      storeToken(data.session.token)
    }
    
    try {
      const response = await request("/auth/session")
      return { user: { ...data.user, ...response } }
    } catch (backendError) {
      return toSession(data.user)
    }
  },

  async signUp({ name, email, password } = {}) {
    const { data, error } = await authClient.signUp.email({ name, email, password })
    if (error) throw new ServiceError(error.message, error.status)
    
    if (data?.session?.token) {
      storeToken(data.session.token)
    }
    
    try {
      const response = await request("/auth/session")
      return { user: { ...data.user, ...response } }
    } catch (backendError) {
      return toSession(data.user)
    }
  },

  async signOut() {
    clearToken()
    await authClient.signOut()
    return null
  },

  // Stub these out or forward them to our own API as needed
  completeOnboarding() {
    return request("/auth/session/onboarding/complete", { method: "POST" })
  },

  async requestPasswordReset({ email } = {}) {
    const { error } = await authClient.forgetPassword({ email })
    if (error) throw new ServiceError(error.message, error.status)
    return true
  },
}

export default authService

