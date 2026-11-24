import fs from "node:fs"
import path from "node:path"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { act } from "react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { w5AuthDocs } from "@/i18n/w5AuthDocs"
import { en as enCopy } from "@/i18n/pricing"
import { PlanCardList } from "../PlanCardList"
import { featureLines, limitLines } from "../planDetails"

const fixtures = vi.hoisted(() => ({ signUp: vi.fn(), createCheckout: vi.fn() }))

vi.mock("@/app/PublicHeader", () => ({ PublicHeader: () => null }))
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ signIn: vi.fn(), signUp: fixtures.signUp, isAuthenticated: false }),
}))
vi.mock("@/services", () => ({ accountService: { createCheckout: fixtures.createCheckout } }))

import { SignUpPage } from "@/pages/auth/SignUpPage"

const PLAN = {
  id: "plan_pro_x", name: "Pro", price_monthly: 49.99, trial_days: 7, checkout: true,
  feature_flags: ["discover", "monitors"],
  limits: { records_per_month: 2000, monitors: 5, alerts_per_day: null },
  pricing: { listed: true, features: { en: [], ar: [] }, tagline: { en: "For teams", ar: "" } },
}

beforeEach(() => {
  vi.restoreAllMocks()
  fixtures.signUp.mockReset()
  fixtures.createCheckout.mockReset()
  localStorage.setItem("helix_lang", "en")
  if (!window.matchMedia) {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: (query) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
    })
  }
})
afterEach(cleanup)

const list = (props) => render(
  <MemoryRouter>
    <PlanCardList plans={[PLAN]} copy={enCopy} lang="en" checkout={{ busyId: null, subscribe: vi.fn() }} {...props} />
  </MemoryRouter>,
)

describe("plan cards show real plan data", () => {
  it("lists only limits the plan really sets and falls back to its real feature flags", () => {
    expect(limitLines(PLAN.limits, enCopy.limitLabels)).toEqual(["Active monitors: 5", "Data records a month: 2,000"])
    expect(limitLines(null, enCopy.limitLabels)).toEqual([])
    expect(featureLines(PLAN, "en", enCopy)).toEqual([enCopy.features.discover, enCopy.features.monitors])
    const written = { ...PLAN, pricing: { ...PLAN.pricing, features: { en: ["Written by the admin"], ar: [] } } }
    expect(featureLines(written, "en", enCopy)).toEqual(["Written by the admin"])
  })

  it("signed out: the card offers the plan's trial and opens sign-up with that plan", () => {
    list({ user: null })
    expect(screen.getByText("7-day free trial · no card")).toBeTruthy()
    const link = screen.getByRole("link", { name: "Start your 7-day free trial" })
    expect(link.getAttribute("href")).toBe("/sign-up?plan=plan_pro_x")
    expect(screen.getByText("$49.99")).toBeTruthy()
  })

  it("a plan without a trial does not promise one", () => {
    list({ user: null, plans: [{ ...PLAN, trial_days: 0 }] })
    expect(screen.queryByText(/free trial/i)).toBeNull()
    expect(screen.getByRole("link", { name: "Get started" })).toBeTruthy()
  })

  it("signed in: Subscribe asks the server for the payment link", () => {
    const subscribe = vi.fn()
    list({ user: { id: "u1" }, checkout: { busyId: null, subscribe } })
    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }))
    expect(subscribe).toHaveBeenCalledWith("plan_pro_x")
  })
})

it("sign-up sends the plan picked on the pricing page", async () => {
  fixtures.signUp.mockResolvedValue({})
  render(
    <MemoryRouter initialEntries={["/sign-up?plan=plan_pro_x"]}>
      <LanguageProvider><SignUpPage /></LanguageProvider>
    </MemoryRouter>,
  )
  const copy = w5AuthDocs.en
  // The way back to sign-in keeps the plan too (checked before submitting: success leaves the page).
  expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/sign-in?plan=plan_pro_x")).toBe(true)
  fireEvent.change(screen.getByLabelText(copy.authFullName), { target: { value: "Owner" } })
  fireEvent.change(screen.getByLabelText(copy.authEmail), { target: { value: "owner@example.test" } })
  fireEvent.change(screen.getByLabelText(copy.authPassword), { target: { value: "secret123" } })
  fireEvent.click(screen.getByRole("checkbox"))
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: copy.authCreateAccountButton }))
  })
  expect(fixtures.signUp).toHaveBeenCalledTimes(1)
  expect(fixtures.signUp.mock.calls[0][0].plan_id).toBe("plan_pro_x")
})

describe("the payment provider is never named in the interface", () => {
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) return entry.name === "__tests__" ? [] : walk(full)
    return /\.(jsx?|json)$/.test(entry.name) ? [full] : []
  })

  it("no source line outside comments mentions it", () => {
    const offenders = []
    for (const file of walk(path.resolve(process.cwd(), "src"))) {
      fs.readFileSync(file, "utf-8").split("\n").forEach((line, i) => {
        const code = line.trim()
        if (/whop/i.test(code) && !/^(\/\/|\/\*|\*)/.test(code)) offenders.push(`${path.relative(process.cwd(), file)}:${i + 1}`)
      })
    }
    expect(offenders).toEqual([])
  })
})
