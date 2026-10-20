// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const { language } = vi.hoisted(() => ({ language: { lang: "en" } }))
vi.mock("@/context/LanguageContext", () => ({ useLanguage: () => language }))

import { JobProgress } from "../JobProgress"

let root, container
function render(props) {
  container = document.createElement("div")
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(<JobProgress {...props} />))
}

beforeEach(() => { language.lang = "en" })
afterEach(() => {
  act(() => root?.unmount())
  root = null
  document.body.replaceChildren()
})

describe("Discover job progress W5 states", () => {
  it("shows the current server stage label rather than a fixed stage label", () => {
    render({
      job: {
        job_id: "job-stage",
        status: "running",
        stage_index: 1,
        stage_label: "Reviewing active campaigns",
        elapsed_ms: 1200,
        records_found: 4,
      },
      query: "shop.example",
    })

    expect(container.textContent).toContain("Reviewing active campaigns")
    expect(container.textContent).not.toContain("resolving sources")
  })

  it("renders the Arabic cancellation terminal and retry action", () => {
    language.lang = "ar"
    const onRetry = vi.fn()
    render({
      job: {
        job_id: "job-cancelled",
        status: "cancelled",
        stage_index: 1,
        stage_label: "Cancelled",
        elapsed_ms: 1200,
        records_found: 4,
      },
      query: "متجر.example",
      onRetry,
    })

    expect(container.textContent).toContain("تم الإلغاء")
    const retry = [...container.querySelectorAll("button")].find(button =>
      button.textContent.includes("إعادة البحث"),
    )
    expect(retry).toBeTruthy()
    act(() => retry.click())
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
