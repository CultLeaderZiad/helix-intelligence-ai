import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { Hero } from "../Hero"
import { LoopsSection } from "../LoopsSection"
import { AccessSection } from "../AccessSection"
import { LegalPage } from "../../../pages/LegalPage"
import { LanguageProvider } from "../../../context/LanguageContext"
import { __setTrialDaysForTests } from "@/hooks/useTrialDays"

function renderInLanguage(language, element) {
  localStorage.setItem("helix_lang", language)
  return renderToStaticMarkup(
    <MemoryRouter>
      <LanguageProvider>{element}</LanguageProvider>
    </MemoryRouter>,
  )
}

describe("W4 marketing and legal disclosures", () => {
  beforeEach(() => { localStorage.clear(); __setTrialDaysForTests(7) })

  it("promises no trial when the server reports trial_days 0 (trial turned off)", () => {
    __setTrialDaysForTests(0)
    const markup = renderInLanguage("en", (
      <>
        <Hero />
        <AccessSection />
      </>
    ))
    expect(markup).not.toMatch(/free trial|7 days free|7-day/i)
    expect(markup).toContain("Create an account")
  })

  it("promises nothing while the trial length is unknown", () => {
    __setTrialDaysForTests(null)
    const markup = renderInLanguage("en", <Hero />)
    expect(markup).not.toMatch(/free trial|days free/i)
    // Nor that access is admin-granted: the trial may well exist.
    expect(markup).not.toMatch(/granted by our team/i)
  })

  it("offers the trial with the server's length when SIGNUP_TRIAL_DAYS is on", () => {
    const markup = renderInLanguage("en", (
      <>
        <Hero />
        <LoopsSection />
        <AccessSection />
      </>
    ))

    expect(markup).not.toMatch(/Nike|Gymshark|Alo Yoga|\b94\s*\/\s*100|\$\s*\d/i)
    // Shown only because the server reported trial_days = 7 (SIGNUP_TRIAL_DAYS).
    expect(markup).toContain("Start your 7-day free trial")
    expect(markup).toContain("No credit card required")
    expect(markup).toContain('href="/sign-up"')
    expect(markup).toContain('id="product"')
    expect(markup).toContain('id="access"')
    expect(markup).toContain('href="#product"')
    expect(markup).toContain("Checkout and payment-provider routes are unavailable")
  })

  it("renders the unapproved legal and processor disclosures in English", () => {
    const markup = renderInLanguage("en", <LegalPage />)

    expect(markup).toContain("not approved")
    expect(markup).toContain("localStorage")
    expect(markup).toContain("end-to-end account deletion path is not established")
    expect(markup).toContain("still require approval")
    expect(markup).toContain('href="mailto:support@cyreax.com"')
    expect(markup).toContain("Cloudflare R2")
    expect(markup).not.toMatch(/\$\s*\d|GDPR|CPRA|Law 151/i)
  })

  it("provides Arabic copy for marketing and legal disclosures", () => {
    const marketing = renderInLanguage("ar", (
      <>
        <Hero />
        <LoopsSection />
        <AccessSection />
      </>
    ))
    const legal = renderInLanguage("ar", <LegalPage />)

    expect(marketing).toContain("لا يقدم Helix حالياً خططاً عامة")
    expect(marketing).toContain("ابدأ تجربتك المجانية لمدة 7 أيام")
    expect(marketing).toContain("7 أيام وصول مجاني دون بطاقة")
    expect(marketing).toContain("اعرف ما يعرضه منافسوك من إعلانات.")
    expect(marketing).toContain("مكتبات الإعلانات")
    expect(legal).toContain("هذه الإفصاحات غير معتمدة")
    expect(legal).toContain("استخدم العنوان أدناه")
    expect(legal).toContain('href="mailto:support@cyreax.com"')
    expect(legal).toContain("localStorage")
  })
})
