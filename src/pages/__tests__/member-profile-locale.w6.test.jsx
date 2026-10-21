import React from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

const fixtures = vi.hoisted(() => ({
  lang: "en",
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
  refreshSession: vi.fn(),
  updateUser: vi.fn(),
}))

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ refreshSession: fixtures.refreshSession, updateUser: fixtures.updateUser }),
}))
vi.mock("@/context/LanguageContext", () => ({
  useLanguage: () => ({ lang: fixtures.lang, t: (_key, fallback) => fallback || _key }),
}))
vi.mock("@/hooks/useProfileSettings", () => ({
  useProfileSettings: () => fixtures.profileState,
}))
vi.mock("@/app/BreadcrumbBar", () => ({ BreadcrumbBar: () => null }))
vi.mock("react-router-dom", () => ({ useNavigate: () => fixtures.navigate }))

import { ProfileSettingsPage } from "../ProfileSettingsPage"

beforeEach(() => {
  fixtures.lang = "en"
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
})
