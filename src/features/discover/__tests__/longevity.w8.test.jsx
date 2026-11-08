// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"

const { language } = vi.hoisted(() => ({ language: { lang: "en", t: (k, f) => f || k } }))
vi.mock("@/context/LanguageContext", () => ({ useLanguage: () => language }))

import { FilterRail, countActiveFilters, LONGEVITY_PRESETS } from "../FilterRail"
import { viewFilters } from "@/hooks/useDiscoverySearch"

let root, container
function render(node) {
  container = document.createElement("div")
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(node))
}
afterEach(() => { act(() => root?.unmount()); container?.remove(); language.lang = "en" })

const base = { country: "ALL", min_days_active: 0, min_score: 0 }

describe("W8 longevity presets", () => {
  it("offers only the presets the results endpoint accepts", () => {
    expect(LONGEVITY_PRESETS).toEqual([0, 30, 60, 90])
    render(<FilterRail filters={base} onChange={() => {}} onClear={() => {}} dirty={false} />)
    const options = [...container.querySelectorAll("#filter-days option")].map((o) => o.textContent)
    expect(options).toEqual(["Any run length", "30+ days", "60+ days", "90+ days"])
    // Platform and format are real search filters now (sent to Metapi); spend band is never shown.
    expect(container.textContent).not.toMatch(/Spend band/)
  })

  it("speaks Arabic and never labels the rubric as a performance score", () => {
    language.lang = "ar"
    render(<FilterRail filters={base} onChange={() => {}} onClear={() => {}} dirty={false} />)
    expect(container.textContent).toContain("مدة التشغيل")
    expect(container.textContent).toContain("ليس توقعًا للأداء")
  })

  it("reports a preset change without touching country", () => {
    const onChange = vi.fn()
    render(<FilterRail filters={base} onChange={onChange} onClear={() => {}} dirty={false} />)
    const select = container.querySelector("#filter-days")
    act(() => { select.value = "60"; select.dispatchEvent(new Event("change", { bubbles: true })) })
    expect(onChange).toHaveBeenCalledWith({ ...base, min_days_active: 60 })
  })

  it("maps page filters to result view parameters", () => {
    expect(viewFilters({ filters: { min_days_active: 30, min_score: 7 } })).toEqual({ min_days: 30, min_score: 7 })
    expect(viewFilters(null)).toEqual({ min_days: 0, min_score: 0 })
    expect(countActiveFilters({ ...base, country: "US", min_days_active: 90 })).toBe(2)
  })
})
