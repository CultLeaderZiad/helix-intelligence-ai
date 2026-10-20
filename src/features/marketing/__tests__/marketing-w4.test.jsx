import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { Hero } from "../Hero"
import { LoopsSection } from "../LoopsSection"
import { PricingSection } from "../PricingSection"
import { LegalPage } from "../../../pages/LegalPage"
import { LanguageProvider } from "../../../context/LanguageContext"

function renderInLanguage(language, element) {
  localStorage.setItem("helix_lang", language)
  return renderToStaticMarkup(
    <MemoryRouter>
      <LanguageProvider>{element}</LanguageProvider>
    </MemoryRouter>,
  )
}

describe("W4 marketing and legal disclosures", () => {
  beforeEach(() => localStorage.clear())

  it("does not present sample scores, brands, trial claims, or public prices", () => {
    const markup = renderInLanguage("en", (
      <>
        <Hero />
        <LoopsSection />
        <PricingSection />
      </>
    ))

    expect(markup).not.toMatch(/Nike|Gymshark|Alo Yoga|\b94\s*\/\s*100|free trial|\$\s*\d/i)
    expect(markup).toContain("Access is granted by an administrator")
    expect(markup).toContain("Checkout and payment-provider routes are unavailable")
  })

  it("renders the unapproved legal and processor disclosures in English", () => {
    const markup = renderInLanguage("en", <LegalPage />)

    expect(markup).toContain("not approved")
    expect(markup).toContain("localStorage")
    expect(markup).toContain("end-to-end account deletion path is not established")
    expect(markup).toContain("pending operator verification")
    expect(markup).toContain("Cloudflare R2")
    expect(markup).not.toContain("mailto:")
    expect(markup).not.toMatch(/\$\s*\d|GDPR|CPRA|Law 151/i)
  })

  it("provides Arabic copy for marketing and legal disclosures", () => {
    const marketing = renderInLanguage("ar", <PricingSection />)
    const legal = renderInLanguage("ar", <LegalPage />)

    expect(marketing).toContain("لا يقدم Helix حالياً خططاً عامة")
    expect(marketing).toContain("يجب أن يمنح المشرف صلاحية الوصول")
    expect(legal).toContain("هذه الإفصاحات غير معتمدة")
    expect(legal).toContain("لا يُنشر عنوان تواصل هنا")
    expect(legal).toContain("localStorage")
  })
})
