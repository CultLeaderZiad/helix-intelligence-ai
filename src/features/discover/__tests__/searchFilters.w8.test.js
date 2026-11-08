import { describe, expect, it } from "vitest"
import { countActiveFilters, searchFiltersDiffer } from "@/features/discover/FilterRail"

describe("search-time filters", () => {
  it("counts each search filter that differs from its default", () => {
    expect(countActiveFilters({ country: "ALL" })).toBe(0)
    expect(
      countActiveFilters({ country: "US", media_type: "video", publisher_platforms: ["instagram"], min_days_active: 30 }),
    ).toBe(4)
    expect(countActiveFilters({ active_status: "", publisher_platforms: [] })).toBe(0)
  })

  it("marks the search stale only when a search-time filter changed", () => {
    const applied = { country: "ALL", min_days_active: 0 }
    expect(searchFiltersDiffer({ ...applied, min_days_active: 60 }, applied)).toBe(false)
    expect(searchFiltersDiffer({ ...applied, start_date_min: "2026-10-01" }, applied)).toBe(true)
    expect(searchFiltersDiffer({ ...applied, content_languages: ["ar"] }, applied)).toBe(true)
  })
})
