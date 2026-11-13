import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { LanguageProvider } from "@/context/LanguageContext"
import { applyLoadedFilters, loadedFilterOptions, EMPTY_LOADED_FILTERS, adStatus } from "../loadedFilters"
import { LoadedResultsFilters } from "../LoadedResultsFilters"
import { MonitorBrandButton } from "../MonitorBrandButton"
import { ShortcutHelp, useResultShortcuts } from "../resultShortcuts"
import { SavedAdAnnotations } from "@/features/boards/SavedAdAnnotations"

const svc = vi.hoisted(() => ({
  previewBrandMonitor: vi.fn(),
  createBrandMonitor: vi.fn(),
  setTags: vi.fn(),
  addNote: vi.fn(),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
  getJobResults: vi.fn(),
  startSearch: vi.fn(),
}))
vi.mock("@/services", () => ({
  monitorService: { previewBrandMonitor: svc.previewBrandMonitor, createBrandMonitor: svc.createBrandMonitor },
  boardService: { setTags: svc.setTags, addNote: svc.addNote, updateNote: svc.updateNote, deleteNote: svc.deleteNote },
  discoverService: { getJobResults: svc.getJobResults, startSearch: svc.startSearch },
}))
const auth = vi.hoisted(() => ({ user: { id: "u1", feature_flags: { monitors: true, swipe_files: true } } }))
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ user: auth.user }) }))

afterEach(() => {
  cleanup()
  localStorage.clear()
  Object.values(svc).forEach((fn) => fn.mockReset())
  auth.user = { id: "u1", feature_flags: { monitors: true, swipe_files: true } }
})

function wrap(node, lang = "en") {
  localStorage.setItem("helix_lang", lang)
  return render(<MemoryRouter><LanguageProvider>{node}</LanguageProvider></MemoryRouter>)
}

const ads = [
  { id: "1", format: "video", cta: "Shop now", landing_domain: "a.com", days_active: 40, last_seen: null },
  { id: "2", format: "image", cta: "Learn more", landing_domain: "b.com", days_active: 3, last_seen: "2026-11-01" },
  { id: "3", format: "video", cta: "Shop now", landing_domain: "b.com", days_active: null, last_seen: null },
]

describe("W9-2 D3 filters on loaded results", () => {
  it("filters by media, status, CTA, domain and run length in memory", () => {
    expect(applyLoadedFilters(ads, EMPTY_LOADED_FILTERS)).toBe(ads)
    expect(applyLoadedFilters(ads, { ...EMPTY_LOADED_FILTERS, format: "video" }).map((a) => a.id)).toEqual(["1", "3"])
    expect(applyLoadedFilters(ads, { ...EMPTY_LOADED_FILTERS, status: "stopped" }).map((a) => a.id)).toEqual(["2"])
    expect(applyLoadedFilters(ads, { ...EMPTY_LOADED_FILTERS, cta: "Shop now", domain: "b.com" }).map((a) => a.id)).toEqual(["3"])
    // Unknown run length is hidden once a minimum is set.
    expect(applyLoadedFilters(ads, { ...EMPTY_LOADED_FILTERS, minDays: 10 }).map((a) => a.id)).toEqual(["1"])
    expect(adStatus(ads[1])).toBe("stopped")
    expect(loadedFilterOptions(ads)).toMatchObject({ formats: ["image", "video"], ctas: ["Learn more", "Shop now"], maxDays: 40 })
  })

  it("changing a control never calls the API", () => {
    const onChange = vi.fn()
    wrap(<LoadedResultsFilters items={ads} filters={EMPTY_LOADED_FILTERS} onChange={onChange} shown={3} />)
    fireEvent.change(screen.getByLabelText("Media"), { target: { value: "video" } })
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_LOADED_FILTERS, format: "video" })
    expect(screen.getByText("Showing 3 of 3 loaded")).toBeTruthy()
    expect(screen.getByText(/Uses 0 records/)).toBeTruthy()
    expect(svc.getJobResults).not.toHaveBeenCalled()
    expect(svc.startSearch).not.toHaveBeenCalled()
  })

  it("renders in Arabic", () => {
    wrap(<LoadedResultsFilters items={ads} filters={EMPTY_LOADED_FILTERS} onChange={() => {}} shown={3} />, "ar")
    expect(screen.getByText(/يستخدم 0 سجل/)).toBeTruthy()
  })
})

const preview = (over = {}) => ({
  query: "123456789", name: "Gymshark", watch: "page_id", cadence: "weekly",
  records_per_run: 30, records_per_month: 150, records_remaining: 180, records_cap: 300,
  fits_this_month: true, existing_monitor_id: null, ...over,
})

describe("W9-2 D2 Monitor this brand", () => {
  it("shows the API's record cost and creates the monitor from the page id", async () => {
    svc.previewBrandMonitor.mockResolvedValue(preview())
    svc.createBrandMonitor.mockResolvedValue({ id: "m1" })
    wrap(<MonitorBrandButton pageId="123456789" brandName="Gymshark" />)
    fireEvent.click(screen.getByRole("button", { name: /Monitor this brand/ }))
    await waitFor(() => expect(screen.getByTestId("monitor-brand-cost").textContent).toMatch(/up to 30 Metapi records, about 150 a month/))
    expect(screen.getByText("180 of 300 records left this month.")).toBeTruthy()
    expect(svc.previewBrandMonitor).toHaveBeenCalledWith({ page_id: "123456789", brand_name: "Gymshark", cadence: "weekly" })
    fireEvent.click(screen.getByRole("button", { name: "Create monitor" }))
    await waitFor(() => expect(screen.getByRole("status").textContent).toMatch(/Monitor created/))
    expect(svc.createBrandMonitor).toHaveBeenCalledWith({ page_id: "123456789", brand_name: "Gymshark", cadence: "weekly" })
  })

  it("blocks creation when the month has no room and explains the cap", async () => {
    svc.previewBrandMonitor.mockResolvedValue(preview({ fits_this_month: false, records_remaining: 4 }))
    wrap(<MonitorBrandButton pageId="123456789" brandName="Gymshark" />)
    fireEvent.click(screen.getByRole("button", { name: /Monitor this brand/ }))
    await waitFor(() => expect(screen.getByText(/Not enough records left/)).toBeTruthy())
    expect(screen.getByRole("button", { name: "Create monitor" }).hasAttribute("disabled")).toBe(true)
  })

  it("shows the record-cap message when the server refuses with 429", async () => {
    svc.previewBrandMonitor.mockResolvedValue(preview())
    svc.createBrandMonitor.mockRejectedValue(Object.assign(new Error("x"), { status: 429, code: "workspace_record_cap_reached" }))
    wrap(<MonitorBrandButton brandName="Acme" />)
    fireEvent.click(screen.getByRole("button", { name: /Monitor this brand/ }))
    await waitFor(() => screen.getByTestId("monitor-brand-cost"))
    fireEvent.click(screen.getByRole("button", { name: "Create monitor" }))
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/monthly Metapi records|Metapi/))
  })

  it("is hidden without the monitors feature", () => {
    auth.user = { id: "u1", feature_flags: { monitors: false, swipe_files: true } }
    wrap(<MonitorBrandButton pageId="1" brandName="X" />)
    expect(screen.queryByRole("button", { name: /Monitor this brand/ })).toBeNull()
  })

  it("renders in Arabic", () => {
    wrap(<MonitorBrandButton brandName="متجر" />, "ar")
    expect(screen.getByRole("button", { name: /راقب هذه العلامة التجارية/ })).toBeTruthy()
  })
})

function ShortcutHarness({ items, selectedId, onSelect, onSave, onOpen }) {
  useResultShortcuts({ enabled: true, items, selectedId, onSelect, onSave, onOpen, onToggleHelp: () => {} })
  return <input aria-label="typing" />
}

describe("W9-2 D9 keyboard shortcuts", () => {
  it("j/k move, s saves, o opens; ignored while typing", () => {
    const onSelect = vi.fn(); const onSave = vi.fn(); const onOpen = vi.fn()
    const items = [{ id: "a" }, { id: "b" }]
    wrap(<ShortcutHarness items={items} selectedId="a" onSelect={onSelect} onSave={onSave} onOpen={onOpen} />)
    fireEvent.keyDown(window, { key: "j" })
    expect(onSelect).toHaveBeenLastCalledWith("b")
    fireEvent.keyDown(window, { key: "k" })
    expect(onSelect).toHaveBeenLastCalledWith("a")
    fireEvent.keyDown(window, { key: "s" })
    expect(onSave).toHaveBeenCalledWith(items[0])
    fireEvent.keyDown(window, { key: "o" })
    expect(onOpen).toHaveBeenCalledWith(items[0])
    fireEvent.keyDown(screen.getByLabelText("typing"), { key: "j" })
    fireEvent.keyDown(window, { key: "s", ctrlKey: true })
    expect(onSelect).toHaveBeenCalledTimes(2)
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it("help popover lists the shortcuts in EN and AR", () => {
    wrap(<ShortcutHelp open onToggle={() => {}} />)
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" }).textContent).toMatch(/Save the selected ad/)
    cleanup()
    wrap(<ShortcutHelp open onToggle={() => {}} />, "ar")
    expect(screen.getByRole("dialog").textContent).toMatch(/حفظ الإعلان المحدد/)
  })
})

describe("W9-2 #7 tags and notes on a board card", () => {
  it("adds and removes tags and notes through the API", async () => {
    svc.setTags.mockResolvedValueOnce({ tags: ["eid", "ugc"] }).mockResolvedValueOnce({ tags: ["ugc"] })
    svc.addNote.mockResolvedValue({ id: "n1", body: "Great hook", author_id: "u1", updated_at: null })
    svc.deleteNote.mockResolvedValue({ deleted: true })
    const onTagsChange = vi.fn()
    wrap(<SavedAdAnnotations creativeId="c1" tags={["eid"]} notes={[]} onTagsChange={onTagsChange} />)
    fireEvent.change(screen.getByLabelText("Add a tag"), { target: { value: " UGC " } })
    fireEvent.click(screen.getByRole("button", { name: "Add tag" }))
    await waitFor(() => expect(screen.getByText("ugc")).toBeTruthy())
    expect(svc.setTags).toHaveBeenCalledWith("c1", ["eid", "ugc"])
    expect(onTagsChange).toHaveBeenCalledWith(["eid", "ugc"])
    fireEvent.click(screen.getByRole("button", { name: "Remove tag eid" }))
    await waitFor(() => expect(screen.queryByText("eid")).toBeNull())

    fireEvent.change(screen.getByLabelText("Why did you save this ad?"), { target: { value: "Great hook" } })
    fireEvent.click(screen.getByRole("button", { name: "Add note" }))
    await waitFor(() => expect(screen.getByText("Great hook")).toBeTruthy())
    expect(svc.addNote).toHaveBeenCalledWith("c1", "Great hook")
    fireEvent.click(screen.getByRole("button", { name: "Delete" }))
    await waitFor(() => expect(screen.queryByText("Great hook")).toBeNull())
  })

  it("keeps the old tags and says so when saving fails", async () => {
    svc.setTags.mockRejectedValue(new Error("boom"))
    wrap(<SavedAdAnnotations creativeId="c1" tags={["eid"]} notes={[]} />)
    fireEvent.change(screen.getByLabelText("Add a tag"), { target: { value: "new" } })
    fireEvent.click(screen.getByRole("button", { name: "Add tag" }))
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/Could not save tags/))
    expect(screen.queryByText("new")).toBeNull()
    expect(screen.getByText("eid")).toBeTruthy()
  })

  it("renders in Arabic", () => {
    wrap(<SavedAdAnnotations creativeId="c1" tags={[]} notes={[]} />, "ar")
    expect(screen.getByLabelText("أضف وسمًا")).toBeTruthy()
  })
})
