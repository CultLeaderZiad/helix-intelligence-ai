import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { act } from "react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { LanguageProvider } from "@/context/LanguageContext"
import { SignInPage } from "@/pages/auth/SignInPage"
import { SignUpPage } from "@/pages/auth/SignUpPage"
import { w5AuthDocs } from "@/i18n/w5AuthDocs"

const fixtures = vi.hoisted(() => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
}))

vi.mock("@/app/PublicHeader", () => ({ PublicHeader: () => null }))
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    signIn: fixtures.signIn,
    signUp: fixtures.signUp,
    isAuthenticated: false,
  }),
}))

beforeEach(() => {
  fixtures.signIn.mockReset()
  fixtures.signUp.mockReset()
  localStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  localStorage.clear()
})

function renderSignIn(lang) {
  localStorage.setItem("helix_lang", lang)
  return render(
    <MemoryRouter>
      <LanguageProvider>
        <SignInPage />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

async function submitSignIn(lang) {
  const copy = w5AuthDocs[lang]
  fireEvent.change(screen.getByLabelText(copy.authEmail), {
    target: { value: "owner@example.test" },
  })
  fireEvent.change(screen.getByLabelText(copy.authPassword), {
    target: { value: "secret" },
  })
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: copy.authSignInButton }))
  })
}

it.each(["en", "ar"])("shows the credential error only for a 401 sign-in in %s", async (lang) => {
  fixtures.signIn.mockRejectedValue(Object.assign(new Error("refused"), { status: 401, code: "http_401" }))
  renderSignIn(lang)
  await submitSignIn(lang)

  const copy = w5AuthDocs[lang]
  expect(await screen.findByText(copy.authSignInFailed)).toBeTruthy()
  expect(screen.queryByText(copy.authServerUnavailable)).toBeNull()
})

it.each(["en", "ar"])("does not call a timeout a bad password in %s", async (lang) => {
  fixtures.signIn.mockRejectedValue(Object.assign(new Error("timeout"), { code: "request_timeout" }))
  renderSignIn(lang)
  await submitSignIn(lang)

  const copy = w5AuthDocs[lang]
  expect(await screen.findByText(copy.authServerUnavailable)).toBeTruthy()
  expect(screen.getByText(copy.authServerUnavailableStatus)).toBeTruthy()
  expect(screen.queryByText(copy.authSignInFailed)).toBeNull()
  expect(screen.queryByText(w5AuthDocs.en.authSignInFailed)).toBeNull()
})

it("keeps the waking copy up while sign-in is still waiting and does not fire a second request", async () => {
  fixtures.signIn.mockReturnValue(new Promise(() => {}))
  vi.useFakeTimers()
  renderSignIn("en")
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authEmail), {
    target: { value: "owner@example.test" },
  })
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authPassword), {
    target: { value: "secret" },
  })
  const button = screen.getByRole("button", { name: w5AuthDocs.en.authSignInButton })
  await act(async () => {
    fireEvent.click(button)
    fireEvent.click(button)
  })

  expect(fixtures.signIn).toHaveBeenCalledTimes(1)
  expect(screen.queryByText(w5AuthDocs.en.authSignInFailed)).toBeNull()

  await act(async () => {
    await vi.advanceTimersByTimeAsync(3000)
  })

  expect(screen.getAllByText(w5AuthDocs.en.authWakingServer).length).toBeGreaterThan(0)
  expect(screen.queryByText(w5AuthDocs.en.authSignInFailed)).toBeNull()
  expect(fixtures.signIn).toHaveBeenCalledTimes(1)
})

it("uses the unavailable message for a sign-up gateway error and the account message for 401", async () => {
  localStorage.setItem("helix_lang", "en")
  fixtures.signUp.mockRejectedValueOnce(Object.assign(new Error("gateway"), { status: 503, code: "server_waking" }))
  render(
    <MemoryRouter>
      <LanguageProvider>
        <SignUpPage />
      </LanguageProvider>
    </MemoryRouter>,
  )

  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authFullName), { target: { value: "Owner" } })
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authEmail), { target: { value: "owner@example.test" } })
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authPassword), { target: { value: "secret123" } })
  fireEvent.click(screen.getByRole("checkbox"))
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: w5AuthDocs.en.authCreateAccountButton }))
  })

  expect(await screen.findByText(w5AuthDocs.en.authServerUnavailable)).toBeTruthy()
  expect(screen.queryByText(w5AuthDocs.en.authSignInFailed)).toBeNull()
  expect(fixtures.signUp).toHaveBeenCalledTimes(1)

  cleanup()
  fixtures.signUp.mockRejectedValueOnce(Object.assign(new Error("refused"), { status: 401, code: "http_401" }))
  render(
    <MemoryRouter>
      <LanguageProvider>
        <SignUpPage />
      </LanguageProvider>
    </MemoryRouter>,
  )
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authFullName), { target: { value: "Owner" } })
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authEmail), { target: { value: "owner@example.test" } })
  fireEvent.change(screen.getByLabelText(w5AuthDocs.en.authPassword), { target: { value: "secret123" } })
  fireEvent.click(screen.getByRole("checkbox"))
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: w5AuthDocs.en.authCreateAccountButton }))
  })

  expect(await screen.findByText(w5AuthDocs.en.authAccountExistsMessage)).toBeTruthy()
  expect(screen.queryByText(w5AuthDocs.en.authServerUnavailable)).toBeNull()
})
