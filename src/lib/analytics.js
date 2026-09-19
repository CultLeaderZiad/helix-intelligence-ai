/**
 * Analytics — privacy-friendly, env-gated, zero-dependency.
 *
 * Uses Plausible by default (cookie-less, GDPR-friendly, no consent banner
 * needed in most jurisdictions — the right default for a B2B tool). It is
 * DISABLED unless `VITE_ANALYTICS_DOMAIN` is set, so local/dev/preview builds
 * never send events.
 *
 * No heavy SDK is installed: we inject Plausible's 1 kB script tag and expose
 * a typed `track()` wrapper that funnels can call (signup, discovery run,
 * upgrade intent). Nothing is tracked when disabled, so `track()` is always
 * safe to call.
 */

const DOMAIN = import.meta.env.VITE_ANALYTICS_DOMAIN
const SCRIPT_SRC = import.meta.env.VITE_ANALYTICS_SCRIPT || "https://plausible.io/js/script.js"

let initialized = false

export function initAnalytics() {
  if (initialized || typeof window === "undefined" || !DOMAIN) return
  initialized = true

  // Queue shim so track() works before the script loads.
  window.plausible =
    window.plausible ||
    function () {
      ;(window.plausible.q = window.plausible.q || []).push(arguments)
    }

  const s = document.createElement("script")
  s.defer = true
  s.dataset.domain = DOMAIN
  s.src = SCRIPT_SRC
  document.head.appendChild(s)
}

/**
 * Track a custom funnel event. No-op when analytics is disabled.
 * @param {string} name  e.g. "signup", "discovery_run", "upgrade_intent"
 * @param {Record<string, string|number>} [props]
 */
export function track(name, props) {
  if (typeof window === "undefined" || !DOMAIN || typeof window.plausible !== "function") return
  window.plausible(name, props ? { props } : undefined)
}

/** SPA pageview on route change — Plausible needs a manual nudge for client routing. */
export function trackPageview(path) {
  if (typeof window === "undefined" || !DOMAIN || typeof window.plausible !== "function") return
  window.plausible("pageview", { u: window.location.origin + path })
}
