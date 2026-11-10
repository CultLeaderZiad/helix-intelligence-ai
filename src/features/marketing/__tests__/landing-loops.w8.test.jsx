import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { LoopsSection } from "../LoopsSection"
import { LanguageProvider } from "../../../context/LanguageContext"

function render(language) {
  localStorage.setItem("helix_lang", language)
  return renderToStaticMarkup(
    <MemoryRouter>
      <LanguageProvider>
        <LoopsSection />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe("W8 landing: four loops with the stacked card motion", () => {
  beforeEach(() => localStorage.clear())

  it("renders four selectable loops and four stacked cards", () => {
    const markup = render("en")
    expect(markup).toContain('id="product"')
    expect(markup).toContain("Four loops,")
    expect(markup).toContain("card-swap-container")
    expect(markup.match(/class="card-swap-item/g)).toHaveLength(4)
    expect(markup.match(/aria-pressed=/g)).toHaveLength(4)
    expect(markup).toContain('aria-pressed="true"')
  })

  it("states product rules instead of sample brands, scores or counts", () => {
    const markup = render("en")
    expect(markup).toContain("never 0")
    expect(markup).toContain("not a performance prediction")
    expect(markup).toContain("1, 7 or 30 days")
    for (const tool of ["search_ads", "get_board", "list_monitor_changes", "get_ad"]) {
      expect(markup).toContain(tool)
    }
    expect(markup).not.toMatch(/Nike|Gymshark|Shopify|TikTok|SCORE:\s*\d|ROAS|\d+(\.\d+)?M\b|free trial|\/create|\/scout/i)
  })

  it("has Arabic copy for the section and the cards", () => {
    const markup = render("ar")
    expect(markup).toContain("أربع حلقات")
    expect(markup).toContain("للقراءة فقط")
    expect(markup).not.toContain("Four loops,")
  })
})
