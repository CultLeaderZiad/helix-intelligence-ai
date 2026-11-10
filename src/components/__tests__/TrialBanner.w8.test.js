import { describe, expect, it } from "vitest"
import { trialBannerState } from "@/components/TrialBanner"
import { daysLeft, extendFrom, toDateInput } from "@/features/admin/ManageAccessDialog"

const NOW = Date.parse("2026-11-08T12:00:00Z")
const DAY = 24 * 60 * 60 * 1000
const user = (over) => ({ access_status: "approved", is_platform_admin: false, ...over })

describe("trial banner", () => {
  it("counts down the last seven days of time-limited access", () => {
    expect(trialBannerState(user({ access_expires_at: new Date(NOW + 7 * DAY).toISOString() }), NOW)).toEqual({ kind: "left", days: 7 })
    expect(trialBannerState(user({ access_expires_at: new Date(NOW + 1.5 * DAY).toISOString() }), NOW)).toEqual({ kind: "left", days: 2 })
    expect(trialBannerState(user({ access_expires_at: new Date(NOW + 3600e3).toISOString() }), NOW)).toEqual({ kind: "today" })
  })

  it("stays quiet for long or open-ended access and for admins", () => {
    expect(trialBannerState(user({ access_expires_at: new Date(NOW + 30 * DAY).toISOString() }), NOW)).toBeNull()
    expect(trialBannerState(user({ access_expires_at: null }), NOW)).toBeNull()
    expect(trialBannerState(user({ is_platform_admin: true, access_status: "expired" }), NOW)).toBeNull()
    expect(trialBannerState(null, NOW)).toBeNull()
  })

  it("says access ended (data kept) after expiry or revocation", () => {
    expect(trialBannerState(user({ access_status: "expired" }), NOW)).toEqual({ kind: "ended" })
    expect(trialBannerState(user({ access_status: "revoked" }), NOW)).toEqual({ kind: "ended" })
  })
})

describe("admin access dates", () => {
  it("extends from the current end while it is in the future, else from now", () => {
    const end = new Date(NOW + 3 * DAY).toISOString()
    expect(toDateInput(extendFrom(end, 7, NOW))).toBe("2026-11-18")
    expect(toDateInput(extendFrom(new Date(NOW - 2 * DAY).toISOString(), 7, NOW))).toBe("2026-11-15")
    expect(toDateInput(extendFrom(null, 30, NOW))).toBe("2026-12-08")
  })

  it("reports whole days left, never negative", () => {
    expect(daysLeft(new Date(NOW + 6.2 * DAY).toISOString(), NOW)).toBe(7)
    expect(daysLeft(new Date(NOW - DAY).toISOString(), NOW)).toBe(0)
    expect(daysLeft(null, NOW)).toBeNull()
  })
})
