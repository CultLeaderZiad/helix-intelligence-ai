import { describe, expect, it } from "vitest"
import { adLibraryUrl } from "../AdvertiserPage"
import { daysSinceUpdate } from "../admin/KnowledgeBasePage"

describe("advertiser Ad Library link", () => {
  it("builds a plain public search URL and encodes the name", () => {
    const url = adLibraryUrl("Nike & Co")
    expect(url).toMatch(/^https:\/\/www\.facebook\.com\/ads\/library\/\?/)
    expect(url).toContain("q=Nike%20%26%20Co")
  })
  it("gives no link without a name", () => {
    expect(adLibraryUrl("  ")).toBeNull()
    expect(adLibraryUrl(null)).toBeNull()
  })
})

describe("knowledge base freshness", () => {
  const now = Date.parse("2026-11-25T00:00:00Z")
  it("counts days since the newest enabled document", () => {
    const docs = [
      { status: "enabled", created_at: "2026-10-01T00:00:00Z" },
      { status: "enabled", created_at: "2026-10-10T00:00:00Z" },
      { status: "disabled", created_at: "2026-11-24T00:00:00Z" },
    ]
    expect(daysSinceUpdate(docs, now)).toBe(46)
  })
  it("is null when nothing is enabled", () => {
    expect(daysSinceUpdate([], now)).toBeNull()
    expect(daysSinceUpdate([{ status: "disabled", created_at: "2026-11-01T00:00:00Z" }], now)).toBeNull()
  })
})
