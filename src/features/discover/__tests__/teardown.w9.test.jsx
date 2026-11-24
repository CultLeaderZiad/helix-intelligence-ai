import React from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import { creativeService } from "@/services"
import { TEARDOWN_COPY, TeardownPanel } from "../TeardownPanel"

const renderPanel = () => render(<LanguageProvider><MemoryRouter><TeardownPanel creativeId="c1" /></MemoryRouter></LanguageProvider>)

describe("AI teardown panel", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem("helix_lang", "en")
  })

  it("shows fields the model left empty as not shown, and the honesty label", async () => {
    vi.spyOn(creativeService, "getTeardown").mockResolvedValue({ hook: "Summer is here", angle: "scarcity", offer: null })
    renderPanel()
    expect(await screen.findByText("Summer is here")).toBeTruthy()
    expect(screen.getAllByText(TEARDOWN_COPY.en.notShown).length).toBeGreaterThan(0)
    expect(screen.getByText(TEARDOWN_COPY.en.label)).toBeTruthy()
  })

  it("reports a failure instead of showing a made-up result", async () => {
    vi.spyOn(creativeService, "getTeardown").mockRejectedValue(new Error("404"))
    vi.spyOn(creativeService, "createTeardown").mockRejectedValue(new Error("502"))
    renderPanel()
    fireEvent.click(screen.getByRole("button", { name: /Analyse this ad/ }))
    expect((await screen.findByRole("alert")).textContent).toBe(TEARDOWN_COPY.en.failed)
  })

  it("has Arabic copy for every field", () => {
    for (const key of Object.keys(TEARDOWN_COPY.en.fields)) expect(TEARDOWN_COPY.ar.fields[key]).toBeTruthy()
  })
})
