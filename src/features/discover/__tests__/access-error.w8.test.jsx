// @vitest-environment jsdom
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { ErrorState } from "@/components/ui/States"
import { Button } from "@/components/ui/Button"
import { Link } from "react-router-dom"
import { LanguageProvider, useLanguage } from "@/context/LanguageContext"

function NeedsAccess() {
  const { t } = useLanguage()
  return <p>{t("discoverNeedsAccess")}</p>
}

describe("W8 Discover access error points at a page that exists", () => {
  it("never sends users to the removed Billing page (EN + AR)", () => {
    for (const lang of ["en", "ar"]) {
      localStorage.setItem("helix_lang", lang)
      const html = renderToStaticMarkup(<LanguageProvider><NeedsAccess /></LanguageProvider>)
      expect(html).not.toMatch(/Billing|الفوترة/)
    }
    localStorage.clear()
  })

  it("ErrorState renders a custom action instead of Retry", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <ErrorState error={{ status: 403, code: "access_pending_approval", message: "Pending" }}
          action={<Button as={Link} to="/access" size="sm">Open Access & Usage</Button>} />
      </MemoryRouter>,
    )
    expect(html).toContain('href="/access"')
    expect(html).not.toContain(">Retry<")
  })
})
