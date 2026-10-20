// @vitest-environment jsdom
import React from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

const { restartOnboarding, getProfile, refreshSession, updateUser, navigate } = vi.hoisted(() => ({
  restartOnboarding: vi.fn(),
  getProfile: vi.fn(),
  refreshSession: vi.fn(),
  updateUser: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock("../../services", () => ({
  accountService: { getProfile },
  authService: { restartOnboarding },
}))
vi.mock("../../context/AuthContext", () => ({ useAuth: () => ({ refreshSession, updateUser }) }))
vi.mock("../../context/LanguageContext", () => ({
  useLanguage: () => ({ lang: "en", t: (_key, fallback) => fallback, isRtl: false }),
}))
vi.mock("react-router-dom", () => ({ useNavigate: () => navigate }))
vi.mock("@/app/BreadcrumbBar", () => ({ BreadcrumbBar: () => null }))

import { ProfileSettingsPage } from "../ProfileSettingsPage"

afterEach(() => {
    cleanup()
    vi.clearAllMocks()
})

describe("profile tour restart", () => {
  it("resets the server state, refreshes the session, and announces the restart", async () => {
    getProfile.mockResolvedValue({ full_name: "", email: "", avatar_url: "", role: "customer" })
    restartOnboarding.mockResolvedValue({ message: "ok" })
    refreshSession.mockResolvedValue(undefined)

    render(<ProfileSettingsPage />)
    fireEvent.click(screen.getByRole("button", { name: "Restart tour" }))

    await waitFor(() => expect(restartOnboarding).toHaveBeenCalledTimes(1))
    expect(refreshSession).toHaveBeenCalledTimes(1)
    expect(updateUser).toHaveBeenCalledWith({ has_completed_onboarding: false })
    expect(navigate).toHaveBeenCalledWith("/discover?tour=restart")
  })
})
