import { useEffect, useState } from "react"
import { pricingService } from "@/services"

/*
 * The sign-up trial length the server grants (GET /public/pricing
 * trial_days; SIGNUP_TRIAL_DAYS). 0 means no trial, the documented default.
 * null while unknown: callers must not promise a trial until the server says so.
 * One request per page load, shared by every caller.
 */
let cached = null
let pending = null

export function __setTrialDaysForTests(value) {
  cached = value
  pending = null
}

function load() {
  if (!pending) {
    pending = pricingService.getPricing()
      .then((data) => {
        const days = Number(data?.trial_days)
        cached = Number.isFinite(days) && days > 0 ? Math.floor(days) : 0
        return cached
      })
      .catch(() => {
        pending = null
        return null
      })
  }
  return pending
}

export function useTrialDays() {
  const [days, setDays] = useState(cached)
  useEffect(() => {
    if (cached !== null) return undefined
    let active = true
    load().then((value) => { if (active) setDays(value) })
    return () => { active = false }
  }, [])
  return days
}

/** "Start your 7-day free trial" with the server's number, or null without a trial. */
export function trialCopy(text, days) {
  return days > 0 ? String(text).replace(/7/g, String(days)) : null
}
