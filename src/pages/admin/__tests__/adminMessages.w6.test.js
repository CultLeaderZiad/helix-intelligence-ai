import { describe, expect, it } from "vitest"
import {
  adminAccessLabel,
  adminMessage,
  formatAdminDate,
  formatAdminDateTime,
  getAdminAccessStatus,
} from "@/i18n/adminMessages"

describe("admin messages and dates", () => {
  it("keeps English copy and localizes Arabic admin access states", () => {
    expect(adminMessage("en", "Pending approval")).toBe("Pending approval")
    expect(adminMessage("ar", "Pending approval")).toBe("بانتظار الموافقة")
    expect(adminAccessLabel("ar", "approved")).toBe("ممنوح من الإدارة")
    expect(adminAccessLabel("ar", "revoked")).toBe("ملغى")
    expect(adminAccessLabel("ar", null)).toBe("حالة الوصول غير متاحة")
    expect(adminAccessLabel("ar", null, false)).toBe("لا توجد مساحة عمل")
  })

  it("reads the explicit access status contract without inferring approval", () => {
    expect(getAdminAccessStatus({ access_status: "approved" })).toBe("approved")
    expect(getAdminAccessStatus({ access: { status: "pending" } })).toBe("pending")
    expect(getAdminAccessStatus({ status: "active" })).toBeNull()
  })

  it("formats valid dates by locale and returns a safe marker for missing or invalid values", () => {
    const date = "2026-01-05T12:30:00Z"
    const english = formatAdminDate(date, "en")
    const arabic = formatAdminDate(date, "ar")

    expect(english).toContain("2026")
    expect(arabic).toMatch(/[\u0600-\u06FF]/)
    expect(arabic).not.toBe(english)
    expect(formatAdminDate(null, "en")).toBe("—")
    expect(formatAdminDate("", "ar")).toBe("—")
    expect(formatAdminDate("not-a-date", "en")).toBe("—")
    expect(formatAdminDateTime(undefined, "ar")).toBe("—")
  })
})
