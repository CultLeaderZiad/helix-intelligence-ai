import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { PlanCard, formatPrice } from "../PricingPage"
import { localized, localizedList, en, ar } from "@/i18n/pricing"
import { limitsFromForm, limitsToForm, linesToList, normalizeCard } from "../admin/PricingAdminPage"

describe("pricing page", () => {
  it("renders a plan as a reflective card with its price, features and call to action", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <PlanCard
          badge="Pro"
          status="Popular"
          name="Team"
          price={formatPrice(29)}
          period="/ month"
          tagline="For growing teams"
          features={["5 monitors", "Unlimited boards"]}
          cta="Start free trial"
          to="/sign-up"
          highlight
        />
      </MemoryRouter>,
    )
    expect(markup).toContain("reflective-card")
    expect(markup).toContain("$29")
    expect(markup).toContain("5 monitors")
    expect(markup).toContain('href="/sign-up"')
    expect(markup).not.toMatch(/checkout|card number/i)
  })

  it("falls back to the other language when an admin left one empty", () => {
    expect(localized({ en: "For teams", ar: "" }, "ar")).toBe("For teams")
    expect(localized({ en: "", ar: "للفرق" }, "en")).toBe("للفرق")
    expect(localizedList({ en: ["a"], ar: [] }, "ar")).toEqual(["a"])
    expect(localized(undefined, "en")).toBe("")
  })

  it("has matching EN and AR copy and promises no checkout", () => {
    expect(Object.keys(ar).sort()).toEqual(Object.keys(en).sort())
    expect(en.body).toMatch(/no credit card/i)
    expect(en.body).toMatch(/no checkout/i)
  })
})

describe("admin pricing editor helpers", () => {
  it("fills every card field so the form stays controlled", () => {
    const card = normalizeCard({ listed: true, features: { en: ["x"] } })
    expect(card.listed).toBe(true)
    expect(card.features).toEqual({ en: ["x"], ar: [] })
    expect(card.badge).toEqual({ en: "", ar: "" })
    expect(normalizeCard(null).cta).toBe("trial")
  })

  it("turns one feature per line into a list, dropping blanks", () => {
    expect(linesToList("  5 monitors \n\nUnlimited boards\n")).toEqual(["5 monitors", "Unlimited boards"])
  })
})


describe("admin plan limits form", () => {
  it("sends blanks as defaults and one cadence only when restricted", () => {
    expect(limitsFromForm({ searches: "", monitors: "", cadences: { daily: true, weekly: true } })).toEqual({
      searches_per_day: null,
      monitors: null,
      monitor_cadences: null,
    })
    expect(limitsFromForm({ searches: "5", monitors: "2", cadences: { daily: false, weekly: true } })).toEqual({
      searches_per_day: 5,
      monitors: 2,
      monitor_cadences: ["weekly"],
    })
  })

  it("round-trips the API shape", () => {
    const form = limitsToForm({ searches_per_day: 20, monitors: 10, monitor_cadences: ["daily"] })
    expect(form).toEqual({ searches: 20, monitors: 10, cadences: { daily: true, weekly: false } })
    expect(limitsToForm(null).cadences).toEqual({ daily: true, weekly: true })
  })
})
