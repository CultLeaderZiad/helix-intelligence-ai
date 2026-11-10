import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { MarketingFooter } from "../MarketingFooter"
import { LanguageProvider } from "../../../context/LanguageContext"

function render(language) {
  localStorage.setItem("helix_lang", language)
  return renderToStaticMarkup(
    <MemoryRouter>
      <LanguageProvider>
        <MarketingFooter />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe("W8 marketing footer", () => {
  beforeEach(() => localStorage.clear())

  it("links only to pages that exist", () => {
    const markup = render("en")
    for (const href of ["/discover", "/monitors", "/swipe-files", "/updates", "/docs", "/#access", "/terms", "/privacy", "/legal/subprocessors", "/cookies", "/agents.md"]) {
      expect(markup).toContain(`href="${href}"`)
    }
    expect(markup).not.toMatch(/href="\/(intelligence|create|performance|scout)"|#pricing|Pricing|Create Studio/)
    expect(markup).toContain("HELIX")
    expect(markup).toContain("Legal disclosures are drafts")
    expect(markup).toContain('href="mailto:support@cyreax.com"')
    expect(markup).toContain("support@cyreax.com")
    expect(markup).not.toContain("no verified privacy contact")
  })

  it("has Arabic copy", () => {
    const markup = render("ar")
    expect(markup).toContain("شروط الخدمة")
    expect(markup).toContain("نسخة تجريبية")
    expect(markup).not.toContain("Terms of Service")
  })
})
