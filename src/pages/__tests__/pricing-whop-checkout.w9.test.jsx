import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import { PlanCard } from "../PricingPage"
import { en, ar } from "@/i18n/pricing"

describe("Whop checkout on the pricing page", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    if (!window.matchMedia) Object.defineProperty(window, "matchMedia", { configurable: true, value: (query) => ({
      matches: false, media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
    }) })
  })

  it("renders a button, not a link, for a plan that can be bought online", () => {
    const onSelect = vi.fn()
    render(
      <MemoryRouter>
        <PlanCard badge="Pro" name="Pro" price="$29" features={[]} cta={en.subscribe} to="/sign-up" onSelect={onSelect} />
      </MemoryRouter>,
    )
    const button = screen.getByRole("button", { name: "Subscribe" })
    fireEvent.click(button)
    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it("disables the button while checkout is opening", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <PlanCard badge="Pro" name="Pro" price="$29" features={[]} cta={en.openingCheckout} to="/" onSelect={() => {}} busy />
      </MemoryRouter>,
    )
    expect(markup).toContain("disabled")
    expect(markup).toContain('aria-busy="true"')
  })

  it("has checkout copy in both languages", () => {
    for (const copy of [en, ar]) {
      for (const key of ["bodyCheckout", "bodyCheckoutNoTrial", "subscribe", "openingCheckout", "checkoutFailed"]) {
        expect(copy[key], key).toBeTruthy()
      }
    }
    expect(en.bodyCheckout).not.toMatch(/no checkout/i)
  })
})
