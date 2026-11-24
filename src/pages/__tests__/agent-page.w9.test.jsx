import React from "react"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import agentService from "@/services/api/agentService.api"
import { AGENT_COPY, AgentPage } from "../AgentPage"

const renderPage = () => render(<LanguageProvider><MemoryRouter><AgentPage /></MemoryRouter></LanguageProvider>)

describe("Ask Helix page", () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem("helix_lang", "en")
    vi.spyOn(agentService, "limits").mockResolvedValue({ messages_used: 1, messages_per_day: 5, generations_used: 0, generations_per_day: 3 })
  })

  it("shows the answer, its sources, and runs a proposal only after approval", async () => {
    vi.spyOn(agentService, "ask").mockResolvedValue({
      answer: "Acme pushes discounts.", citations: [{ type: "kb", id: "chunk1" }],
      proposals: [{ type: "create_monitor", summary: "Monitor 'acme' (weekly)", requires_approval: true,
                   request: { method: "POST", path: "/monitors", body: { query: "acme" } } }],
    })
    const approve = vi.spyOn(agentService, "approve").mockResolvedValue([{}])
    renderPage()
    expect(await screen.findByText("1 of 5 questions used today · 0 of 3 generations used today")).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText(AGENT_COPY.en.placeholder), { target: { value: "What is Acme doing?" } })
    fireEvent.click(screen.getByRole("button", { name: /Ask/ }))
    expect(await screen.findByText("Acme pushes discounts.")).toBeTruthy()
    expect(screen.getByText(/kb:chunk1/)).toBeTruthy()
    expect(approve).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole("button", { name: /Approve/ }))
    expect(await screen.findByRole("button", { name: /Done/ })).toBeTruthy()
    expect(approve).toHaveBeenCalledTimes(1)
  })

  it("shows the server's error instead of a made-up answer", async () => {
    vi.spyOn(agentService, "ask").mockRejectedValue({ detail: { message: "The assistant could not answer right now." } })
    renderPage()
    fireEvent.change(screen.getByPlaceholderText(AGENT_COPY.en.placeholder), { target: { value: "hi" } })
    fireEvent.click(screen.getByRole("button", { name: /Ask/ }))
    expect((await screen.findByRole("alert")).textContent).toBe("The assistant could not answer right now.")
  })

  it("has Arabic copy for every key", () => {
    for (const key of Object.keys(AGENT_COPY.en)) expect(AGENT_COPY.ar[key], key).toBeTruthy()
  })
})
