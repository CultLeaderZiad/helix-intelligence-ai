import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { RecordMeter } from "../RecordMeter"
import { ArchiveSearch } from "../ArchiveSearch"
import { StoredResultsPrompt } from "../StoredResultsPrompt"

const { search } = vi.hoisted(() => ({ search: vi.fn() }))
vi.mock("@/services", () => ({ archiveService: { search } }))
afterEach(() => { cleanup(); localStorage.clear(); search.mockReset() })

const usage = (over = {}) => ({
  period_start: "2026-11-01", used: 120, cap: 300, remaining: 180, percent: 40,
  warning: false, reached: false,
  estimates: { discover_search: 30, monitor_run: 30, monitor_month: { daily: 930, weekly: 150 } },
  ...over,
})

function wrap(node, lang = "en") {
  localStorage.setItem("helix_lang", lang)
  return render(<LanguageProvider>{node}</LanguageProvider>)
}

describe("W9-1 record meter", () => {
  it("shows the API's numbers and no warning under 80%", () => {
    wrap(<RecordMeter usage={usage()} error={false} />)
    expect(screen.getByText(/120 of 300 records used/)).toBeTruthy()
    expect(screen.getByRole("meter").getAttribute("aria-valuenow")).toBe("120")
    expect(screen.queryByRole("alert")).toBeNull()
  })
  it("warns at 80% and says clearly when the cap is reached", () => {
    wrap(<RecordMeter usage={usage({ used: 250, remaining: 50, percent: 83, warning: true })} error={false} />)
    expect(screen.getByRole("alert").textContent).toMatch(/80% or more/)
    cleanup()
    wrap(<RecordMeter usage={usage({ used: 300, remaining: 0, percent: 100, warning: true, reached: true })} error={false} />)
    expect(screen.getByRole("alert").textContent).toMatch(/used all of its monthly records/)
  })
  it("says the meter is unavailable instead of inventing numbers", () => {
    wrap(<RecordMeter usage={null} error />)
    expect(screen.getByText(/unavailable/)).toBeTruthy()
    expect(screen.queryByRole("meter")).toBeNull()
  })
  it("renders in Arabic", () => {
    wrap(<RecordMeter usage={usage()} error={false} />, "ar")
    expect(screen.getByText(/سجلات Metapi هذا الشهر/)).toBeTruthy()
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
