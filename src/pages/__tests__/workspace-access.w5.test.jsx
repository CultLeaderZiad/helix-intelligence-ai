import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { BillingPage } from "../BillingPage"

const { state } = vi.hoisted(() => ({ state: { status: "pending", flags: {} } }))
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ user: { feature_flags: state.flags } }) }))
vi.mock("@/hooks/useWorkspaceAccess", () => ({ useWorkspaceAccess: () => ({
  access: { status: state.status }, usage: null, loading: false, error: false,
  submitting: false, refresh: vi.fn(), requestAccess: vi.fn(),
}) }))
afterEach(() => { cleanup(); localStorage.clear() })

describe("W5 access, not purchase", () => {
  it("explains manual approval without trial, prices or checkout", () => {
    state.status = "pending"
    render(<LanguageProvider><BillingPage /></LanguageProvider>)
    expect(screen.getByRole("heading", { name: "Access & Usage" })).toBeTruthy()
    expect(screen.getByText(/Access is granted by an administrator, not purchased/)).toBeTruthy()
    expect(screen.queryByText(/select a plan|free trial|checkout|\$\d/i)).toBeNull()
    expect(screen.getByText(/What happens next/)).toBeTruthy()
  })
  it("W8: lists each feature with the workspace's real on/off state", () => {
    state.status = "approved"
    state.flags = { discover: true, monitors: false }
    render(<LanguageProvider><BillingPage /></LanguageProvider>)
    const rows = screen.getAllByRole("listitem").map((li) => li.textContent)
    expect(rows[0]).toMatch(/^on\s*Discover/)
    expect(rows[1]).toMatch(/^off\s*Monitors/)
    expect(rows[2]).toMatch(/^off\s*Boards/)
    expect(screen.queryByText(/What happens next/)).toBeNull()
    state.flags = {}
  })
  it("renders an approved state in Arabic with no request button", () => {
    state.status = "approved"
    localStorage.setItem("helix_lang", "ar")
    render(<LanguageProvider><BillingPage /></LanguageProvider>)
    expect(screen.getByRole("heading", { name: "الوصول والاستخدام" })).toBeTruthy()
    expect(screen.queryByRole("button", { name: /إرسال/ })).toBeNull()
  })
})
