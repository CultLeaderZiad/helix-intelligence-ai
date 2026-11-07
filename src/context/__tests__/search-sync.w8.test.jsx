import { act, cleanup, renderHook, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const authState = vi.hoisted(() => ({ user: null }))
const api = vi.hoisted(() => ({
  listDrafts: vi.fn(),
  listRecentJobs: vi.fn(),
  saveDraft: vi.fn(),
  deleteDraft: vi.fn(),
  getJobResults: vi.fn(),
}))
vi.mock("../AuthContext", () => ({ useAuth: () => authState }))
vi.mock("@/services", () => ({ discoverService: api }))

import { SearchProvider, useSearchContext } from "../SearchContext"

const render = () => renderHook(() => useSearchContext(), { wrapper: SearchProvider })

describe("W8 drafts and history sync with the server", () => {
  beforeEach(() => {
    authState.user = { id: "u1", organization_id: "o1", feature_flags: { discover: true } }
    api.listDrafts.mockResolvedValue({ items: [{ id: "d1", title: "Q4", query: "nike", notes: "90d", filters: { country: "US" }, created_at: "2026-11-06T10:00:00Z" }] })
    api.listRecentJobs.mockResolvedValue({ items: [
      { job_id: "j1", query: "nike", status: "succeeded", records_found: 12, created_at: "2026-11-06T09:00:00Z" },
      { job_id: "j2", query: "adidas", status: "failed", records_found: 0, created_at: "2026-11-06T08:00:00Z" },
    ] })
  })
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    localStorage.clear()
    authState.user = null
  })

  it("loads drafts and history from the server for a Discover workspace", async () => {
    const { result } = render()
    await waitFor(() => expect(result.current.serverSynced).toBe(true))
    expect(result.current.drafts.map((d) => [d.id, d.query, d.requirements, d.server])).toEqual([["d1", "nike", "90d", true]])
    expect(result.current.searchHistory.map((h) => [h.query, h.job_id, h.total, h.status])).toEqual([
      ["nike", "j1", 12, "succeeded"],
      ["adidas", "j2", 0, "failed"],
    ])
  })

  it("saves and deletes drafts through the API", async () => {
    api.saveDraft.mockResolvedValue({ id: "d2", title: "New", query: "puma", notes: "", filters: {}, created_at: "2026-11-06T11:00:00Z" })
    api.deleteDraft.mockResolvedValue({ deleted: "d1" })
    const { result } = render()
    await waitFor(() => expect(result.current.serverSynced).toBe(true))
    await act(() => result.current.saveDraft({ title: "New", query: "puma", filters: { min_days_active: 30 } }))
    expect(api.saveDraft).toHaveBeenCalledWith({ title: "New", query: "puma", notes: "", filters: { min_days_active: 30 } })
    expect(result.current.drafts.map((d) => d.id)).toEqual(["d2", "d1"])
    await act(() => result.current.deleteDraft("d1"))
    expect(api.deleteDraft).toHaveBeenCalledWith("d1")
    expect(result.current.drafts.map((d) => d.id)).toEqual(["d2"])
  })

  it("restores a draft when the server refuses to delete it", async () => {
    api.deleteDraft.mockRejectedValue(new Error("nope"))
    const { result } = render()
    await waitFor(() => expect(result.current.serverSynced).toBe(true))
    await act(async () => {
      await expect(result.current.deleteDraft("d1")).rejects.toThrow("nope")
    })
    expect(result.current.drafts.map((d) => d.id)).toEqual(["d1"])
  })

  it("re-opens a past search from stored results, and reports when there is nothing to open", async () => {
    api.getJobResults.mockResolvedValue({ items: [{ id: "c1" }, { id: "c2" }], total: 12, took_ms: 5 })
    const { result } = render()
    await waitFor(() => expect(result.current.serverSynced).toBe(true))
    let opened
    await act(async () => { opened = await result.current.openSearchSession(result.current.searchHistory[0]) })
    expect(opened).toBe(true)
    expect(api.getJobResults).toHaveBeenCalledWith("j1", { page: 1, page_size: 20 })
    expect(result.current.latestSearch.items).toHaveLength(2)
    await act(async () => { opened = await result.current.openSearchSession(result.current.searchHistory[1]) })
    expect(opened).toBe(false)
  })

  it("keeps drafts local when the workspace is not granted Discover", async () => {
    authState.user = { id: "u1", organization_id: "o1", feature_flags: { discover: false } }
    const { result } = render()
    await act(() => result.current.saveDraft({ query: "local only" }))
    expect(api.listDrafts).not.toHaveBeenCalled()
    expect(api.saveDraft).not.toHaveBeenCalled()
    expect(result.current.drafts[0].query).toBe("local only")
  })
})

describe("W8 draft delete vs. a refresh already in flight", () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    localStorage.clear()
    authState.user = null
  })

  it("does not bring back a draft deleted while an older refresh was loading", async () => {
    authState.user = { id: "u1", organization_id: "o1", feature_flags: { discover: true } }
    api.listRecentJobs.mockResolvedValue({ items: [] })
    api.listDrafts.mockResolvedValueOnce({ items: [{ id: "d1", title: "A", query: "a", created_at: "2026-11-06T10:00:00Z" }] })
    const { result } = render()
    await waitFor(() => expect(result.current.drafts.map((d) => d.id)).toEqual(["d1"]))

    let release
    api.listDrafts.mockReturnValueOnce(new Promise((resolve) => { release = resolve }))
    api.deleteDraft.mockResolvedValue({ deleted: "d1" })
    let refresh
    act(() => { refresh = result.current.refreshFromServer() })
    await act(() => result.current.deleteDraft("d1"))
    await act(async () => {
      release({ items: [{ id: "d1", title: "A", query: "a", created_at: "2026-11-06T10:00:00Z" }] })
      await refresh
    })
    expect(result.current.drafts).toEqual([])
  })
})
