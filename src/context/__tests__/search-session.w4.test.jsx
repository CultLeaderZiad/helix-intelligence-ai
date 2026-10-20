import { act, cleanup, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

const authState = vi.hoisted(() => ({ user: null }))
vi.mock("../AuthContext", () => ({ useAuth: () => authState }))

import { SearchProvider, useSearchContext } from "../SearchContext"

const cacheKeys = (scope) => [
  `helix_latest_search_${scope}`,
  `helix_search_history_${scope}`,
  `helix_active_creative_${scope}`,
  `helix_saved_drafts_${scope}`,
]

describe("private search cache lifecycle", () => {
  afterEach(() => {
    cleanup()
    authState.user = null
    localStorage.clear()
  })

  it("purges the current user and organization cache on session clearing", () => {
    const scope = "user-a:org-a"
    cacheKeys(scope).forEach((key) => localStorage.setItem(key, "{}"))
    authState.user = { id: "user-a", organization_id: "org-a" }
    const { result } = renderHook(() => useSearchContext(), { wrapper: SearchProvider })

    act(() => window.dispatchEvent(new Event("helix:session-clearing")))

    expect(cacheKeys(scope).map((key) => localStorage.getItem(key))).toEqual([
      null,
      null,
      null,
      null,
    ])
    expect(result.current.latestSearch).toBeNull()
    expect(result.current.searchHistory).toEqual([])
    expect(result.current.activeCreative).toBeNull()
    expect(result.current.drafts).toEqual([])
  })

  it("does not expose a different user's cache after account switching", async () => {
    const firstScope = "user-a:org-a"
    const secondScope = "user-b:org-b"
    const firstHistory = [{ query: "first account" }]
    const secondHistory = [{ query: "second account" }]
    localStorage.setItem(`helix_search_history_${firstScope}`, JSON.stringify(firstHistory))
    localStorage.setItem(`helix_search_history_${secondScope}`, JSON.stringify(secondHistory))
    authState.user = { id: "user-a", organization_id: "org-a" }
    const { result, rerender } = renderHook(() => useSearchContext(), { wrapper: SearchProvider })
    expect(result.current.searchHistory).toEqual(firstHistory)

    authState.user = { id: "user-b", organization_id: "org-b" }
    rerender()

    expect(result.current.searchHistory).toEqual(secondHistory)
  })
})
