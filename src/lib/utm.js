/**
 * UTM & Referral Attribution Tracker
 * 
 * Captures campaign parameters (utm_source, utm_medium, utm_campaign, 
 * utm_term, utm_content, ref, referrer) on any landing page visit,
 * persists them in localStorage across client-side navigation, and attaches
 * them to user registration payloads.
 */

const STORAGE_KEY = "helix_signup_attribution"

/**
 * Capture UTM and referrer parameters from URL search params or document.referrer.
 * Safe to call on every route change or app mount.
 */
export function captureAttribution() {
  if (typeof window === "undefined") return

  try {
    const urlParams = new URLSearchParams(window.location.search)
    const utmSource = urlParams.get("utm_source")
    const utmMedium = urlParams.get("utm_medium")
    const utmCampaign = urlParams.get("utm_campaign")
    const utmTerm = urlParams.get("utm_term")
    const utmContent = urlParams.get("utm_content")
    const ref = urlParams.get("ref") || urlParams.get("referrer")

    // Only update if there are actual campaign parameters in the current URL
    if (utmSource || utmMedium || utmCampaign || ref) {
      const attribution = {
        utm_source: utmSource || undefined,
        utm_medium: utmMedium || undefined,
        utm_campaign: utmCampaign || undefined,
        utm_term: utmTerm || undefined,
        utm_content: utmContent || undefined,
        referrer: ref || (document.referrer ? new URL(document.referrer).hostname : undefined),
        landing_page: window.location.pathname,
        captured_at: new Date().toISOString(),
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution))
      return attribution
    }

    // If no existing attribution is stored and external document.referrer is present, store referrer
    const existing = localStorage.getItem(STORAGE_KEY)
    if (!existing && document.referrer) {
      try {
        const refUrl = new URL(document.referrer)
        if (refUrl.hostname && refUrl.hostname !== window.location.hostname) {
          const attribution = {
            utm_source: refUrl.hostname.replace(/^www\./, ''),
            utm_medium: 'referral',
            referrer: document.referrer,
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
    return typeof parsed === "object" && parsed !== null ? parsed : {}
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
