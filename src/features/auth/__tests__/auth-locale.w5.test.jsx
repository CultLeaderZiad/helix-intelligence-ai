import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { LanguageProvider } from "@/context/LanguageContext"
import { SignInPage } from "@/pages/auth/SignInPage"
import { w5AuthDocs } from "@/i18n/w5AuthDocs"

vi.mock("@/app/PublicHeader", () => ({ PublicHeader: () => null }))
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ signIn: vi.fn(), isAuthenticated: false }) }))
vi.mock("@/services", () => ({ ServiceError: class extends Error {} }))
afterEach(() => { cleanup(); localStorage.clear() })

it.each(["en", "ar"])("renders localized sign-in and real form validation in %s", (lang) => {
  localStorage.setItem("helix_lang", lang)
  render(<MemoryRouter><LanguageProvider><SignInPage /></LanguageProvider></MemoryRouter>)
  expect(screen.getByRole("heading", { name: w5AuthDocs[lang].authSignInTitle })).toBeTruthy()
  fireEvent.submit(document.querySelector("form"))
  expect(screen.getAllByText(w5AuthDocs[lang].authFieldRequired)).toHaveLength(2)
  expect(document.documentElement.dir).toBe(lang === "ar" ? "rtl" : "ltr")
})
