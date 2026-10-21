import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { LanguageProvider } from "@/context/LanguageContext"
import { adminAccessLabel, adminMessage } from "@/i18n/adminMessages"
import { AccessRequestsPage } from "@/pages/admin/AccessRequestsPage"
import { AuditLogPage } from "@/pages/admin/AuditLogPage"

const adminServiceMock = vi.hoisted(() => ({
  listAccessRequests: vi.fn(),
  listPlans: vi.fn(),
  approveAccessRequest: vi.fn(),
  rejectAccessRequest: vi.fn(),
  revokeOrganizationAccess: vi.fn(),
  getUsageLogsFiltered: vi.fn(),
}))

vi.mock("@/services", () => ({ adminService: adminServiceMock }))

const request = {
  id: "request-1",
  org_id: "workspace-1",
  requested_features: ["discover", "intelligence"],
  note: "Synthetic review request",
}

const auditEvent = {
  id: "event-12345678",
  operation: "discover_job_start",
  provider: "gemini_media",
  user_id: "user-1",
  credits_deducted: 1.5,
  cost_usd: 0.0123,
  created_at: "2026-09-01T12:00:00Z",
}

function renderLocalized(page, lang) {
  localStorage.setItem("helix_lang", lang)
  return render(<LanguageProvider>{page}</LanguageProvider>)
}

beforeEach(() => {
  adminServiceMock.listAccessRequests.mockResolvedValue([request])
  adminServiceMock.listPlans.mockResolvedValue([{ id: "internal-config-id", name: "Hidden internal configuration" }])
  adminServiceMock.approveAccessRequest.mockResolvedValue({ status: "approved" })
  adminServiceMock.rejectAccessRequest.mockResolvedValue({ status: "rejected" })
  adminServiceMock.revokeOrganizationAccess.mockResolvedValue({ status: "revoked" })
  adminServiceMock.getUsageLogsFiltered.mockResolvedValue({ items: [auditEvent], total: 1, page: 1, has_more: false })
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.clearAllMocks()
})

describe("W6 admin access requests localization", () => {
  it.each(["en", "ar"])("localizes pending access requests and hides internal plan configuration in %s", async (lang) => {
    const { container } = renderLocalized(<AccessRequestsPage />, lang)
    const expected = (english) => adminMessage(lang, english)

    expect(await screen.findByRole("heading", { name: expected("Access requests") })).toBeTruthy()
    expect(screen.getByText(expected("Admin-granted feature access"))).toBeTruthy()
    expect(screen.getByText(adminAccessLabel(lang, "pending"))).toBeTruthy()
    expect(screen.getByLabelText(expected("Discover Search"))).toBeTruthy()
    expect(screen.getByRole("button", { name: expected("Approve access") })).toBeTruthy()
    expect(screen.getByRole("button", { name: expected("Reject request") })).toBeTruthy()
    expect(container.firstElementChild.getAttribute("dir")).toBe(lang === "ar" ? "rtl" : "ltr")
    expect(container.textContent).not.toContain("Hidden internal configuration")
    expect(container.textContent).not.toMatch(/trial|select a plan|checkout/i)
  })

  it("retains the admin grant API payload without exposing plan choices", async () => {
    renderLocalized(<AccessRequestsPage />, "en")
    await screen.findByRole("button", { name: "Approve access" })
    fireEvent.click(screen.getByLabelText("Discover Search"))
    fireEvent.click(screen.getByRole("button", { name: "Approve access" }))

    await waitFor(() => expect(adminServiceMock.approveAccessRequest).toHaveBeenCalledWith("request-1", {
      plan_id: "internal-config-id",
      feature_flags: expect.objectContaining({ discover: true }),
      expires_at: null,
    }))
    expect(screen.queryByRole("combobox")).toBeNull()
  })

  it.each(["en", "ar"])("localizes access-request empty and error states in %s", async (lang) => {
    adminServiceMock.listAccessRequests.mockResolvedValueOnce([])
    const { unmount } = renderLocalized(<AccessRequestsPage />, lang)
    expect(await screen.findByText(adminMessage(lang, "No pending access requests."))).toBeTruthy()
    unmount()

    adminServiceMock.listAccessRequests.mockRejectedValueOnce(new Error("internal service detail"))
    renderLocalized(<AccessRequestsPage />, lang)
    expect(await screen.findByRole("alert")).toHaveTextContent(adminMessage(lang, "Unable to load access requests."))
  })
})

describe("W6 admin audit log localization", () => {
  it.each(["en", "ar"])("localizes audit filters, event details, and RTL direction in %s", async (lang) => {
    const { container } = renderLocalized(<AuditLogPage />, lang)
    const expected = (english) => adminMessage(lang, english)

    expect(await screen.findByRole("heading", { name: expected("Audit Trail & Operation Logs") })).toBeTruthy()
    expect(screen.getByRole("combobox", { name: expected("Provider") })).toBeTruthy()
    expect(screen.getByRole("combobox", { name: expected("Operation") })).toBeTruthy()
    expect(screen.getByPlaceholderText(expected("Filter by User ID or organization ID"))).toBeTruthy()
    expect(screen.getByText(adminMessage(lang, "Discover search"))).toBeTruthy()
    expect(container.firstElementChild.getAttribute("dir")).toBe(lang === "ar" ? "rtl" : "ltr")

    fireEvent.click(container.querySelector("tbody tr"))
    expect(screen.getByRole("dialog", { name: expected("Audit Event Inspector") })).toBeTruthy()
    expect(screen.getByText(adminMessage(lang, "Gemini Media"))).toBeTruthy()
    expect(screen.getByRole("button", { name: expected("Close") })).toBeTruthy()
  })

  it.each(["en", "ar"])("localizes audit empty and error states in %s", async (lang) => {
    adminServiceMock.getUsageLogsFiltered
      .mockRejectedValueOnce(new Error("internal service detail"))
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, has_more: false })
    renderLocalized(<AuditLogPage />, lang)

    expect(await screen.findByRole("alert")).toHaveTextContent(adminMessage(lang, "Unable to load audit events."))
    fireEvent.click(screen.getByRole("button", { name: adminMessage(lang, "Retry") }))
    expect(await screen.findByText(adminMessage(lang, "No audit events match filters"))).toBeTruthy()
    expect(screen.getByText(adminMessage(lang, "Try resetting the provider or operation criteria."))).toBeTruthy()
  })
})
