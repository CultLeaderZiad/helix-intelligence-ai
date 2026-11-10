/**
 * UTM & Referral Attribution Tracker
 * 
 * Captures campaign parameters (utm_source, utm_medium, utm_campaign, 
 * utm_term, utm_content, ref, referrer) on any landing page visit,
 * persists them in localStorage across client-side navigation, and attaches
 * them to user registration payloads.
 */

const STORAGE_KEY = "helix_signup_attribution"

const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/i

function sanitizeParam(val) {
  if (!val || typeof val !== "string") return undefined
  const trimmed = val.trim()
  if (!trimmed || EMAIL_REGEX.test(trimmed)) return undefined
  return trimmed
}

function sanitizeReferrer(rawRef) {
  if (!rawRef || typeof rawRef !== "string") return undefined
  const trimmed = rawRef.trim()
  if (!trimmed || EMAIL_REGEX.test(trimmed)) return undefined

  try {
    const url = new URL(trimmed)
    // Strip query string and fragment to avoid leaking tokens or PII from cross-origin referrers
    return `${url.origin}${url.pathname}`
  } catch {
    return trimmed
  }
}

/**
 * Capture UTM and referrer parameters from URL search params or document.referrer.
 * Safe to call on every route change or app mount.
 */
export function captureAttribution() {
  if (typeof window === "undefined") return

  try {
    const urlParams = new URLSearchParams(window.location.search)
    const utmSource = sanitizeParam(urlParams.get("utm_source"))
    const utmMedium = sanitizeParam(urlParams.get("utm_medium"))
    const utmCampaign = sanitizeParam(urlParams.get("utm_campaign"))
    const utmTerm = sanitizeParam(urlParams.get("utm_term"))
    const utmContent = sanitizeParam(urlParams.get("utm_content"))
    const rawRef = urlParams.get("ref") || urlParams.get("referrer")
    const ref = sanitizeReferrer(rawRef)

    // F72: Include utm_term and utm_content so term/content-only campaigns are not dropped
    if (utmSource || utmMedium || utmCampaign || utmTerm || utmContent || ref) {
      let referrerVal = ref
      if (!referrerVal && document.referrer) {
        try {
          const docRefUrl = new URL(document.referrer)
          referrerVal = docRefUrl.hostname
        } catch {}
      }

      const attribution = {
        utm_source: utmSource || undefined,
        utm_medium: utmMedium || undefined,
        utm_campaign: utmCampaign || undefined,
        utm_term: utmTerm || undefined,
        utm_content: utmContent || undefined,
        referrer: referrerVal || undefined,
        landing_page: window.location.pathname,
        captured_at: new Date().toISOString(),
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution))
      return attribution
    }

    // If no existing attribution is stored and external document.referrer is present, store referrer with stripped query
    const existing = localStorage.getItem(STORAGE_KEY)
    if (!existing && document.referrer) {
      try {
        const refUrl = new URL(document.referrer)
        if (refUrl.hostname && refUrl.hostname !== window.location.hostname) {
          const attribution = {
            utm_source: refUrl.hostname.replace(/^www\./, ''),
            utm_medium: 'referral',
            referrer: `${refUrl.origin}${refUrl.pathname}`,
            landing_page: window.location.pathname,
            captured_at: new Date().toISOString(),
          }
          localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution))
          return attribution
        }
      } catch {}
    }
  } catch (err) {
    console.warn("Failed to capture attribution:", err)
  }
}

/**
 * Retrieve captured attribution parameters for signup.
 * @returns {Record<string, string>}
 */
export function getAttribution() {
  if (typeof window === "undefined") return {}

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (typeof parsed !== "object" || parsed === null) return {}

    /** @type {Record<string, string>} */
    const cleaned = {}
    for (const [k, v] of Object.entries(parsed)) {
      if (typeof v === "string" && !EMAIL_REGEX.test(v)) {
        cleaned[k] = v
      }
    }
    return cleaned
  } catch {
    return {}
  }
}

/**
 * Clear attribution data after successful registration.
 */
export function clearAttribution() {
  if (typeof window === "undefined") return
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {}
}
