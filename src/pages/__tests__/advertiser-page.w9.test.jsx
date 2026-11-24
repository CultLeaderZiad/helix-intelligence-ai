import React from "react"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import advertiserService from "@/services/api/advertiserService.api"
import { ADVERTISER_COPY, AdvertiserPage } from "../AdvertiserPage"

function renderPage() {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={["/advertisers/acme"]}>
        <Routes><Route path="/advertisers/:brandId" element={<AdvertiserPage />} /></Routes>
      </MemoryRouter>
    </LanguageProvider>,
  )
}

describe("Advertiser page", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem("helix_lang", "en")
  })

  it("shows unknown values as Unknown, never as 0, and explains the order", async () => {
    vi.spyOn(advertiserService, "getSummary").mockResolvedValue({
      brand_id: "acme", brand_name: "Acme", ads_found: 2, longest_running_days: null,
      active_now: null, launches_last_30d: null, weekly: [],
    })
    vi.spyOn(advertiserService, "getAds").mockResolvedValue({
      items: [{ id: "1", headline: "Summer sale", body: "", signals: { days_active: null, variants: 1, landing_page_reuse: null } }],
      has_more: false,
    })
    renderPage()
    expect(await screen.findByText("Acme")).toBeTruthy()
    expect(screen.getAllByText("Unknown").length).toBeGreaterThan(2)
    expect(screen.getByText(ADVERTISER_COPY.en.noMonitor)).toBeTruthy()
    expect(screen.getByText(ADVERTISER_COPY.en.order)).toBeTruthy()
    expect(screen.queryByText(/score/i)).toBeTruthy() // only the "not a score" sentence
  })

  it("says so when the advertiser cannot be loaded", async () => {
    vi.spyOn(advertiserService, "getSummary").mockRejectedValue(new Error("404"))
    vi.spyOn(advertiserService, "getAds").mockRejectedValue(new Error("404"))
    renderPage()
    expect((await screen.findByRole("alert")).textContent).toBe(ADVERTISER_COPY.en.failed)
  })

  it("has Arabic copy for every key", () => {
    for (const key of Object.keys(ADVERTISER_COPY.en)) expect(ADVERTISER_COPY.ar[key], key).toBeTruthy()
  })
})
