import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { toRecordUsage } from "@/hooks/useRecordUsage"
import { ArchiveSearch } from "../ArchiveSearch"
import { StoredResultsPrompt } from "../StoredResultsPrompt"

const { search } = vi.hoisted(() => ({ search: vi.fn() }))
vi.mock("@/services", () => ({ archiveService: { search } }))
afterEach(() => { cleanup(); localStorage.clear(); search.mockReset() })

function wrap(node, lang = "en") {
  localStorage.setItem("helix_lang", lang)
  return render(<LanguageProvider>{node}</LanguageProvider>)
}

describe("W9-1 record usage reads main's counter", () => {
  it("maps /account/usage/today fields and never invents numbers", () => {
    expect(toRecordUsage({
      records_used_this_month: 120, records_cap_this_month: 150, records_remaining_this_month: 30,
      records_warning: true, platform_records_paused: false,
      records_estimates: { discover_search: 45 },
    })).toEqual({ used: 120, cap: 150, remaining: 30, warning: true, platformPaused: false, estimates: { discover_search: 45 } })
    expect(toRecordUsage(null)).toBeNull()
    expect(toRecordUsage({ searches_run_today: 2 })).toBeNull()
  })
})

describe("W9-1 archive search", () => {
  it("searches the archive and lists real results", async () => {
    search.mockResolvedValue({
      query: "shorts", records_used: 0,
      archive: { total: 1, items: [{ id: "1", brand_name: "Gymshark", headline: "Shorts", body: "Run", archived_at: "2026-11-02T00:00:00Z", permalink: "https://www.facebook.com/ads/library/?id=1" }] },
      saved: { total: 0, items: [] },
    })
    wrap(<ArchiveSearch />)
    fireEvent.change(screen.getByRole("searchbox", { name: "Search your archive" }), { target: { value: " shorts " } })
    fireEvent.click(screen.getByRole("button", { name: "Search archive" }))
    await waitFor(() => expect(screen.getByText(/Gymshark · Shorts/)).toBeTruthy())
    expect(search).toHaveBeenCalledWith("shorts", { scope: "all", page_size: 20 })
    expect(screen.getByText(/Uses 0 records/)).toBeTruthy()
  })
  it("says when nothing matches", async () => {
    search.mockResolvedValue({ query: "zz", archive: { total: 0, items: [] }, saved: null })
    wrap(<ArchiveSearch />)
    fireEvent.change(screen.getByRole("searchbox", { name: "Search your archive" }), { target: { value: "zz" } })
    fireEvent.click(screen.getByRole("button", { name: "Search archive" }))
    await waitFor(() => expect(screen.getByText(/No archived ads match "zz"/)).toBeTruthy())
  })
})

describe("W9-1 stored results first", () => {
  it("offers stored results for 0 records next to a fresh run with its estimate", () => {
    const onView = vi.fn()
    const onFresh = vi.fn()
    wrap(<StoredResultsPrompt stored={{ job_id: "j", total: 12, searched_at: "2026-11-10T08:00:00Z" }} estimate={30} onView={onView} onFresh={onFresh} onCancel={vi.fn()} />)
    expect(screen.getByText(/12 ads from a search on 2026-11-10/)).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: "View stored results (0 records)" }))
    fireEvent.click(screen.getByRole("button", { name: "Run fresh search (up to 30 records)" }))
    expect(onView).toHaveBeenCalledOnce()
    expect(onFresh).toHaveBeenCalledOnce()
  })
  it("renders nothing without a stored search", () => {
    const { container } = wrap(<StoredResultsPrompt stored={null} estimate={30} onView={() => {}} onFresh={() => {}} onCancel={() => {}} />)
    expect(container.textContent).toBe("")
  })
})
