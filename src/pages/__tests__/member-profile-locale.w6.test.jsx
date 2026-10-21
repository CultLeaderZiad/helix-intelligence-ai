import React from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

const fixtures = vi.hoisted(() => ({
  lang: "en",
  authUser: { organization_id: "workspace-1" },
  location: { pathname: "/sign-in", state: null },
  profileState: {
    profile: { full_name: "Ada", email: "ada@example.test", avatar_url: "", role: "member" },
    setProfile: vi.fn(),
    isLoadingProfile: false,
    loadError: false,
    isSaving: false,
    isUploadingAvatar: false,
    uploadAvatar: vi.fn(),
    saveProfile: vi.fn(),
    restartOnboarding: vi.fn(),
  },
  navigate: vi.fn(),
  signOut: vi.fn(),
  signIn: vi.fn(),
  refreshSession: vi.fn(),
  updateUser: vi.fn(),
}))

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: fixtures.authUser,
    signOut: fixtures.signOut,
    signIn: fixtures.signIn,
    isAuthenticated: false,
    refreshSession: fixtures.refreshSession,
    updateUser: fixtures.updateUser,
  }),
}))
vi.mock("@/context/LanguageContext", () => ({
  useLanguage: () => ({ lang: fixtures.lang, isRtl: fixtures.lang === "ar", t: (_key, fallback) => fallback || _key }),
}))
vi.mock("@/hooks/useProfileSettings", () => ({
  useProfileSettings: () => fixtures.profileState,
}))
vi.mock("@/app/BreadcrumbBar", () => ({ BreadcrumbBar: () => null }))
vi.mock("@/app/PublicHeader", () => ({ PublicHeader: () => null }))
vi.mock("react-router-dom", async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => fixtures.navigate,
  useLocation: () => fixtures.location,
}))

import { ProfileSettingsPage } from "../ProfileSettingsPage"
import { SignInPage } from "../auth/SignInPage"
import { getMemberMessage } from "@/i18n/memberMessages"

beforeEach(() => {
  fixtures.lang = "en"
  fixtures.authUser = { organization_id: "workspace-1" }
  fixtures.location = { pathname: "/sign-in", state: null }
  vi.clearAllMocks()
})

afterEach(() => cleanup())

describe("member profile localization", () => {
  it("renders English copy and left-to-right direction", () => {
    const { container } = render(<ProfileSettingsPage />)
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Account & profile settings")
    expect(container.querySelector("[dir='ltr']")).not.toBeNull()
  })

  it("renders Arabic body copy and right-to-left direction", () => {
    fixtures.lang = "ar"
    const { container } = render(<ProfileSettingsPage />)
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("إعدادات الحساب والملف الشخصي")
    expect(screen.getByText("المعلومات الشخصية")).not.toBeNull()
    expect(screen.getByLabelText("الاسم الكامل")).not.toBeNull()
    expect(container.querySelector("[dir='rtl']")).not.toBeNull()
  })

  it("hides profile writes without a workspace while keeping account details and tour controls", () => {
    fixtures.authUser = { organization_id: null }
    render(<ProfileSettingsPage />)

    expect(screen.getByRole("status").textContent).toBe(getMemberMessage("en", "profileWorkspaceAssignmentRequired"))
    expect(screen.getByLabelText("Full name").hasAttribute("disabled")).toBe(true)
    expect(screen.queryByRole("button", { name: "Upload new photo" })).toBeNull()
    expect(screen.queryByLabelText("New password")).toBeNull()
    expect(screen.queryByRole("button", { name: "Save settings" })).toBeNull()
    expect(screen.getByRole("button", { name: /restart/i })).toBeTruthy()
  })

  it("signs out after a successful password change and carries the reauthentication notice", async () => {
    fixtures.profileState.saveProfile.mockResolvedValueOnce({ status: "ok", user: { full_name: "Ada" } })
    render(<ProfileSettingsPage />)

    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "old-password" } })
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "new-password-123" } })
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "new-password-123" } })
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }))

    await waitFor(() => expect(fixtures.signOut).toHaveBeenCalledOnce())
    expect(fixtures.profileState.saveProfile).toHaveBeenCalledWith({
      fullName: "Ada",
      avatarUrl: "",
      currentPassword: "old-password",
      newPassword: "new-password-123",
    })
    expect(fixtures.refreshSession).not.toHaveBeenCalled()
    expect(fixtures.navigate).toHaveBeenCalledWith("/sign-in", {
      replace: true,
      state: { email: "ada@example.test", passwordChanged: true },
    })
  })

  it("shows a localized password-change confirmation on sign-in in both languages", () => {
    for (const lang of ["en", "ar"]) {
      fixtures.lang = lang
      fixtures.location = { pathname: "/sign-in", state: { email: "ada@example.test", passwordChanged: true } }
      const { unmount } = render(<MemoryRouter><SignInPage /></MemoryRouter>)
      expect(screen.getByRole("status").textContent).toContain(getMemberMessage(lang, "profilePasswordChanged"))
      unmount()
    }
  })

  it("does not claim a password change or sign out when the server rejects the update", async () => {
    fixtures.profileState.saveProfile.mockRejectedValueOnce(new Error("server rejected update"))
    render(<ProfileSettingsPage />)

    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "old-password" } })
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "new-password-123" } })
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "new-password-123" } })
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }))

    expect((await screen.findByRole("alert")).textContent).toContain("Could not update your profile.")
    expect(fixtures.signOut).not.toHaveBeenCalled()
    expect(fixtures.navigate).not.toHaveBeenCalled()
  })
})
