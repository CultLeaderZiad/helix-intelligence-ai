import { describe, expect, it, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("motion/react", () => ({ motion: new Proxy({}, { get: () => ({ children }) => <div>{children}</div> }) }))
vi.mock("@/context/LanguageContext", () => ({ useLanguage: () => ({ lang: "en" }) }))
vi.mock("@/context/SearchContext", () => ({ useSearchContext: () => ({ drafts: [{ id: "d1", title: "Summer sale angle", query: "shoes" }] }) }))
vi.mock("@/services", () => ({
  creativeService: {
    getSavedCreatives: vi.fn().mockResolvedValue({ items: [
      { id: "a", headline: "Rival landing page", data_source: "manual_upload", landing_domain: "rival.com/promo" },
      { id: "b", headline: "Ad with page", permalink: "https://www.facebook.com/ads/library/?id=1" },
      { id: "c", headline: "Plain saved ad", data_source: "meta" },
    ] }),
  },
}))

import { DraftsFolder, linkFor, pickLinks } from "../DraftsFolder"

describe("linkFor", () => {
  it("uses the permalink, or the site of a manual reference, and nothing else", () => {
    expect(linkFor({ permalink: "https://x.com/a" })).toBe("https://x.com/a")
    expect(linkFor({ data_source: "manual_upload", landing_domain: "rival.com/promo" })).toBe("https://rival.com/promo")
    expect(linkFor({ data_source: "meta", landing_domain: "shop.com" })).toBeNull()
    expect(linkFor({ permalink: "javascript:alert(1)" })).toBeNull()
  })
  it("never links a non-http address", () => {
    expect(pickLinks([{ id: "x", headline: "bad", permalink: "javascript:alert(1)" }]).every((l) => /^https?:/.test(l.href))).toBe(true)
  })
})

describe("DraftsFolder", () => {
  it("lists draft titles and saved links when opened", async () => {
    render(<MemoryRouter><DraftsFolder /></MemoryRouter>)
    fireEvent.click(screen.getByRole("button", { name: "Drafts and links" }))
    expect(screen.getByText("Summer sale angle")).toBeTruthy()
    await waitFor(() => expect(screen.getByText("Rival landing page")).toBeTruthy())
    expect(screen.getByText("Ad with page")).toBeTruthy()
    expect(screen.queryByText("Plain saved ad")).toBeNull()
  })
})
