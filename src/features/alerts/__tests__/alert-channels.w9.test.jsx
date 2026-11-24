import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { accountService } from "@/services"
import { ALERT_COPY, AlertChannelsSection } from "../AlertChannelsSection"

function renderSection() {
  return render(<LanguageProvider><AlertChannelsSection /></LanguageProvider>)
}

describe("Alert channels settings", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem("helix_lang", "en")
  })

  it("shows the server's channels and daily usage, never a made-up number", async () => {
    vi.spyOn(accountService, "listAlertChannels").mockResolvedValue({
      items: [{ id: "c1", type: "webhook", status: "disabled", label: "https://hooks.example.com/…", enabled: true, last_error: "webhook answered HTTP 500" }],
      limits: { telegram: 1, webhook: 1, per_day: 20 },
      sent_today: 3,
      telegram_available: false,
    })
    renderSection()
    expect(await screen.findByText("https://hooks.example.com/…")).toBeTruthy()
    expect(screen.getByText("3 of 20 alerts sent today")).toBeTruthy()
    expect(screen.getByText(/Turned off after failures/)).toBeTruthy()
    expect(screen.getByText(ALERT_COPY.en.telegramOff)).toBeTruthy()
  })

  it("shows an error instead of an empty list when loading fails", async () => {
    vi.spyOn(accountService, "listAlertChannels").mockRejectedValue(new Error("down"))
    renderSection()
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(ALERT_COPY.en.failed))
    expect(screen.queryByText(ALERT_COPY.en.empty)).toBeNull()
  })

  it("has Arabic copy for every key", () => {
    for (const key of Object.keys(ALERT_COPY.en)) expect(ALERT_COPY.ar[key], key).toBeTruthy()
  })
})
