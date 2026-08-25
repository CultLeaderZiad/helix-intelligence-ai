import { ServiceError } from "../http"
import { delay, maybeFail, makeId } from "./latency"

/**
 * Mock auth service.
 *
 * Stands in for the FastAPI auth endpoints and satisfies the exact same
 * interface as authService.api.js, so flipping VITE_DATA_SOURCE=api needs
 * zero context/page changes.
 *
 * MOCK-ONLY details that the real backend replaces:
 *   - Passwords are compared in plaintext here. Server-side this is an
 *     Argon2/bcrypt hash the client never sees.
 *   - The "session token" is persisted to sessionStorage to survive a
 *     reload. In production this is an httpOnly, Secure cookie set by the
 *     server — never readable JS. Everything the app needs (the public
 *     user object) still comes back through getSession().
 */

/* Namespaced so this module is the only thing that touches the key. */
const SESSION_KEY = "helix.session"

/**
 * Seed accounts so both roles are reachable without a signup:
 *   admin@helix.io    / helix-admin     -> admin
 *   analyst@helix.io  / helix-analyst   -> customer
 */
const SEED_USERS = [
  {
    id: "usr_admin",
    name: "Dana Okafor",
    email: "admin@helix.io",
    password: "helix-admin",
    role: "admin",
  },
  {
    id: "usr_analyst",
    name: "Ravi Menon",
    email: "analyst@helix.io",
    password: "helix-analyst",
    role: "customer",
  },
]

/** Registry lives in-memory for the session; signups append to it. */
const users = new Map(SEED_USERS.map((u) => [u.email.toLowerCase(), u]))

/** Strip the password before anything leaves the service boundary. */
function publicUser(u) {
  return {
    id: u.id, name: u.name, email: u.email, role: u.role,
    credit_balance: 25.0, trial_days_remaining: 7,
    daily_credit_limit: 3.5, daily_credits_used: 0.0, daily_credits_remaining: 3.5,
    daily_credits_resets_at_utc: null,
    plan_id: "plan_trial_default",
    feature_flags: { discover: true, intelligence: true, create: true, performance: true, swipe_files: true },
  }
}

function persistSession(user) {
  try {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ token: makeId("tok"), user: publicUser(user) }),
    )
  } catch {
    /* storage unavailable (private mode); session simply won't survive reload */
  }
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    /* nothing to clear */
  }
}

function readSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed?.user ?? null
  } catch {
    return null
  }
}

/* ------------------------------------------------------------------ */
/* Public interface — must match authService.api.js exactly           */
/* ------------------------------------------------------------------ */

const authService = {
  /**
   * Resolve the current session from the persisted token, if any.
   * Returns null when unauthenticated — it never throws for "not signed
   * in", because that is a normal state, not an error.
   * @returns {Promise<{ user: import('../contracts').AuthUser }|null>}
   */
  async getSession() {
    await delay(120)
    const user = readSession()
    return user ? { user } : null
  },

  /**
   * @param {import('../contracts').Credentials} credentials
   * @returns {Promise<{ user: import('../contracts').AuthUser }>}
   */
  async signIn({ email, password } = {}) {
    await delay(320)
    maybeFail("Authentication service unavailable")

    const rec = users.get(String(email ?? "").trim().toLowerCase())
    if (!rec || rec.password !== password) {
      throw new ServiceError("Invalid email or password", {
        status: 401,
        code: "invalid_credentials",
      })
    }

    persistSession(rec)
    return { user: publicUser(rec) }
  },

  /**
   * New accounts are always created as 'customer'. Elevation to 'admin'
   * is a back-office action, never something a public signup can grant.
   * @param {import('../contracts').SignUpParams} params
   * @returns {Promise<{ user: import('../contracts').AuthUser }>}
   */
  async signUp({ name, email, password } = {}) {
    await delay(360)
    maybeFail("Authentication service unavailable")

    const key = String(email ?? "").trim().toLowerCase()
    if (users.has(key)) {
      throw new ServiceError("An account with that email already exists", {
        status: 409,
        code: "email_taken",
      })
    }

    const rec = {
      id: makeId("usr"),
      name: String(name ?? "").trim(),
      email: key,
      password,
      role: "customer",
    }
    users.set(key, rec)
    persistSession(rec)
    return { user: publicUser(rec) }
  },

  /**
   * Idempotent — signing out an already-signed-out client is fine.
   * @returns {Promise<null>}
   */
  async signOut() {
    await delay(80)
    clearSession()
    return null
  },

  /**
   * Always resolves ok, even for an unknown email: revealing whether an
   * address is registered is an account-enumeration leak. The UI shows
   * the same confirmation either way.
   * @param {{ email: string }} params
   * @returns {Promise<{ ok: true, email: string }>}
   */
  async requestPasswordReset({ email } = {}) {
    await delay(300)
    maybeFail("Authentication service unavailable")
    return { ok: true, email: String(email ?? "").trim().toLowerCase() }
  },
}

export default authService
