import { cleanup, render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { afterEach, describe, expect, it, vi } from "vitest"

const { state } = vi.hoisted(() => ({ state: { lang: "en", result: null } }))
vi.mock("@/context/LanguageContext", () => ({ useLanguage: () => ({ lang: state.lang, t: (k, f) => f || k }) }))
vi.mock("@/services", () => ({
  boardService: { getGuestBoard: vi.fn(() => (state.result instanceof Error ? Promise.reject(state.result) : Promise.resolve(state.result))) },
}))

import { GuestBoardPage } from "../GuestBoardPage"

function open(token = "tok.sig") {
  return render(
    <MemoryRouter initialEntries={[`/b/${token}`]}>
      <Routes><Route path="/b/:token" element={<GuestBoardPage />} /></Routes>
    </MemoryRouter>,
  )
}
afterEach(() => { cleanup(); state.lang = "en"; document.head.querySelectorAll('meta[name="referrer"],meta[name="robots"]').forEach((m) => m.remove()) })

const board = {
  board: "Hooks", read_only: true, expires_at: "2026-12-01T00:00:00+00:00", total: 2,
  items: [
    { id: "a", brand_name: "Acme", platform: "meta", format: "image", headline: "Long runner", body: "", days_active: 45, text_rubric_score: 7.5 },
    { id: "b", brand_name: "Acme", platform: "meta", format: "image", headline: "No start date", body: "", days_active: null, text_rubric_score: null },
  ],
}

describe("W8 guest board page", () => {
  it("shows a read-only board with honest run length and no editing controls", async () => {
    state.result = board
    open()
    expect(await screen.findByRole("heading", { name: "Hooks" })).toBeTruthy()
    expect(screen.getByText("Read-only board")).toBeTruthy()
    expect(screen.getByText("unknown")).toBeTruthy()
    expect(screen.queryByRole("button")).toBeNull()
    expect(document.head.querySelector('meta[name="referrer"]')?.getAttribute("content")).toBe("no-referrer")
    expect(document.head.querySelector('meta[name="robots"]')?.getAttribute("content")).toContain("noindex")
  })

  it("explains a revoked or expired link in Arabic", async () => {
    state.lang = "ar"
    state.result = new Error("404")
    open()
    expect(await screen.findByText("انتهت صلاحية هذا الرابط أو تم إلغاؤه")).toBeTruthy()
  })
})
