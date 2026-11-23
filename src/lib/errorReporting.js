/*
 * Optional Sentry error reporting for the SPA. Off unless VITE_SENTRY_DSN is
 * set at build time; the SDK is then loaded as a separate chunk, so builds
 * without a DSN ship no Sentry code on the main path.
 * Errors only (no tracing, no session replay) to stay inside the free tier.
 * Every event is scrubbed: auth headers, cookies, tokens and emails never leave
 * the browser.
 */

const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g
const SENSITIVE = ["authorization", "cookie", "password", "token", "secret", "api_key", "apikey", "email"]
const FILTERED = "[Filtered]"
// Secret-bearing query parameters (reset/invite links carry ?token=...), masked
// wherever they appear in a string: request URLs, navigation breadcrumbs.
const SECRET_PARAM_RE = /(^|[?&;\s])(token|access_token|refresh_token|code|secret|password|api_key|apikey|key|signature|sig)=([^&#\s;"']+)/gi

const isSensitive = (key) => SENSITIVE.some((s) => String(key).toLowerCase().includes(s))

export function scrub(value) {
  if (Array.isArray(value)) return value.map(scrub)
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, isSensitive(k) ? FILTERED : scrub(v)]),
    )
  }
  if (typeof value === "string") {
    return value.replace(EMAIL_RE, "[email]").replace(SECRET_PARAM_RE, (_m, pre, name) => `${pre}${name}=${FILTERED}`)
  }
  return value
}

export function beforeSend(event) {
  const next = { ...event }
  if (next.request) {
    const { cookies: _c, data: _d, ...request } = next.request
    next.request = request
  }
  if (next.user) next.user = next.user.id ? { id: next.user.id } : {}
  return scrub(next)
}

/** @param {Record<string, string | undefined>} [env] */
export async function initErrorReporting(env = import.meta.env) {
  const dsn = (env?.VITE_SENTRY_DSN || "").trim()
  if (!dsn) return false
  try {
    const Sentry = await import("@sentry/react")
    Sentry.init({
      dsn,
      environment: env.MODE,
      // Collect no user info, cookies, headers or bodies (Sentry v11 dataCollection).
      dataCollection: { userInfo: false, cookies: false, httpHeaders: false, httpBodies: [] },
      tracesSampleRate: 0,
      beforeSend,
      beforeBreadcrumb: (crumb) => scrub(crumb),
    })
    return true
  } catch {
    return false
  }
}
