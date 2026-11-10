import { cleanup, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { LegalPage } from "@/pages/LegalPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe("VITE_SUPPORT_EMAIL", () => {
  it("defaults to support@cyreax.com", async () => {
    vi.stubEnv("VITE_SUPPORT_EMAIL", "")
    vi.resetModules()
    const mod = await import("../supportEmail.js")
    expect(mod.SUPPORT_EMAIL).toBe("support@cyreax.com")
    expect(mod.SUPPORT_MAILTO).toBe("mailto:support@cyreax.com")
  })

  it("uses a valid override and ignores a value that is not an email", async () => {
    vi.stubEnv("VITE_SUPPORT_EMAIL", " help@example.com ")
    vi.resetModules()
    const overridden = await import("../supportEmail.js")
    expect(overridden.SUPPORT_EMAIL).toBe("help@example.com")

    vi.stubEnv("VITE_SUPPORT_EMAIL", "not-an-email")
    vi.resetModules()
    const fallback = await import("../supportEmail.js")
    expect(fallback.SUPPORT_EMAIL).toBe("support@cyreax.com")
  })
})

describe("support address in the UI", () => {
  it("publishes a mailto on the legal contact section in English and Arabic", () => {
    localStorage.setItem("helix_lang", "en")
    const { unmount } = render(
      <MemoryRouter>
        <LanguageProvider>
          <LegalPage />
        </LanguageProvider>
      </MemoryRouter>,
    )
    const link = screen.getAllByRole("link", { name: "support@cyreax.com" })[0]
    expect(link.getAttribute("href")).toBe("mailto:support@cyreax.com")
    expect(screen.getByText(/use the address below/)).toBeTruthy()
    expect(screen.queryByText(/No contact address is published/)).toBeNull()
    unmount()

    localStorage.setItem("helix_lang", "ar")
    render(
      <MemoryRouter>
        <LanguageProvider>
          <LegalPage />
        </LanguageProvider>
      </MemoryRouter>,
    )
    expect(screen.getByText(/استخدم العنوان أدناه/)).toBeTruthy()
    expect(screen.getAllByRole("link", { name: "support@cyreax.com" }).length).toBeGreaterThan(0)
  })

  it("shows the support mailto on the not-found page", () => {
    render(
      <MemoryRouter>
        <LanguageProvider>
          <NotFoundPage />
        </LanguageProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole("link", { name: "support@cyreax.com" }).getAttribute("href")).toBe("mailto:support@cyreax.com")
  })
})
