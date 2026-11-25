import React from "react"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import agentService from "@/services/api/agentService.api"
import { AGENT_COPY, AgentPage, ASSISTANT_NAME, mentionAt } from "../AgentPage"

const renderPage = () => render(<LanguageProvider><MemoryRouter><AgentPage /></MemoryRouter></LanguageProvider>)

const SEARCH = { type: "search", id: "gym shoes", label: "gym shoes", hint: "Search · 12 ads · 2026-11-20" }
const DRAFT = { type: "draft", id: "d1", label: "Ramadan plan", hint: "Draft · رمضان عروض" }
const ANSWER = { answer: "Acme pushes discounts.", citations: [], proposals: [], assistant: "Cyreax-Z.1", references_used: [] }

// The page also has the draft form's text boxes, so the prompt box is found by its slot.
function textbox() {
  return /** @type {HTMLTextAreaElement} */ (document.querySelector('[data-slot="prompt-box-input"]'))
}

function typeInto(text) {
  const box = textbox()
  fireEvent.change(box, { target: { value: text } })
  return box
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.setItem("helix_lang", "en")
  // Reduced motion keeps the prompt box deterministic in jsdom.
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query) => ({ matches: /reduced-motion/.test(query), media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
  })
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
  vi.spyOn(agentService, "limits").mockResolvedValue({ messages_used: 1, messages_per_day: 5, generations_used: 0, generations_per_day: 3 })
  vi.spyOn(agentService, "mentions").mockResolvedValue({ items: [SEARCH, DRAFT] })
})
afterEach(cleanup)

describe("Ask Helix prompt box", () => {
  it("shows the assistant name in the model picker and the real usage", async () => {
    renderPage()
    expect(ASSISTANT_NAME).toBe("Cyreax-Z.1")
    expect(screen.getByRole("button", { name: "Model: Cyreax-Z.1" })).toBeTruthy()
    expect(await screen.findByText("1 of 5 questions used today · 0 of 3 generations used today")).toBeTruthy()
  })

  it("typing @ offers the user's own things; picking one attaches it and removes the @ text", async () => {
    renderPage()
    typeInto("compare @gym")
    expect(await screen.findByRole("option", { name: /gym shoes/ })).toBeTruthy()
    expect(agentService.mentions).toHaveBeenCalledWith("gym")
    fireEvent.click(screen.getByRole("option", { name: /gym shoes/ }))
    expect(screen.getByRole("list", { name: "Based on" }).textContent).toContain("gym shoes")
    expect(textbox().value).toBe("compare ")
    expect(screen.queryByRole("listbox")).toBeNull()
  })

  it("sends the attached references and the chosen effort, and shows the answer", async () => {
    const ask = vi.spyOn(agentService, "ask").mockResolvedValue({ ...ANSWER, references_used: [{ type: "draft", id: "d1", label: "Ramadan plan" }] })
    renderPage()
    typeInto("@ramadan")
    fireEvent.click(await screen.findByRole("option", { name: /Ramadan plan/ }))
    typeInto("What should I change?")
    fireEvent.click(screen.getByRole("button", { name: "Send, hold to think harder" }))
    await waitFor(() => expect(ask).toHaveBeenCalledTimes(1))
    const [question, , lang, options] = ask.mock.calls[0]
    expect(question).toBe("What should I change?")
    expect(lang).toBe("en")
    expect(options.references).toEqual([{ type: "draft", id: "d1", label: "Ramadan plan" }])
    expect(options.effort).toBe("quick")   // a tap sends at the first effort
    expect(await screen.findByText("Acme pushes discounts.")).toBeTruthy()
    expect(screen.getByText(/Cyreax-Z\.1 · AI answer based on your workspace data/)).toBeTruthy()
  })

  it("a quick-start window attaches the user's latest search and asks at once", async () => {
    const ask = vi.spyOn(agentService, "ask").mockResolvedValue(ANSWER)
    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Analyse my latest search" }))
    await waitFor(() => expect(ask).toHaveBeenCalledTimes(1))
    const [question, , , options] = ask.mock.calls[0]
    expect(question).toBe(AGENT_COPY.en.shortcuts.search.prompt)
    expect(options.references).toEqual([{ type: "search", id: "gym shoes", label: "gym shoes" }])
    expect(options.effort).toBe("think")
    expect(await screen.findByText("Acme pushes discounts.")).toBeTruthy()
  })

  it("a quick-start window says what is missing instead of asking about nothing", async () => {
    // No search, no monitor, no board: only a draft exists.
    vi.spyOn(agentService, "mentions").mockResolvedValue({ items: [DRAFT] })
    const ask = vi.spyOn(agentService, "ask")
    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "What changed in my monitor?" }))
    expect((await screen.findByRole("alert")).textContent).toBe(AGENT_COPY.en.shortcutNeeds.monitor)
    expect(ask).not.toHaveBeenCalled()
  })

  it("shows the working state, and Stop ends it without a made-up answer", async () => {
    vi.spyOn(agentService, "ask").mockImplementation((_q, _h, _l, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" })))
    }))
    renderPage()
    typeInto("hello")
    fireEvent.click(screen.getByRole("button", { name: "Send, hold to think harder" }))
    expect(await screen.findByText("Analysing…")).toBeTruthy()
    fireEvent.click(await screen.findByRole("button", { name: "Stop" }))
    expect(await screen.findByText("Stopped.")).toBeTruthy()
    expect(screen.queryByText("Analysing…")).toBeNull()
  })

  it("shows the server's error instead of an answer", async () => {
    vi.spyOn(agentService, "ask").mockRejectedValue({ detail: { message: "The assistant could not answer right now." } })
    renderPage()
    typeInto("hi")
    fireEvent.click(screen.getByRole("button", { name: "Send, hold to think harder" }))
    expect((await screen.findByRole("alert")).textContent).toBe("The assistant could not answer right now.")
  })

  it("runs a proposal only after the user approves it", async () => {
    vi.spyOn(agentService, "ask").mockResolvedValue({
      ...ANSWER,
      proposals: [{ type: "create_monitor", summary: "Monitor 'acme' (weekly)", requires_approval: true, request: { method: "POST", path: "/monitors", body: { query: "acme" } } }],
    })
    const approve = vi.spyOn(agentService, "approve").mockResolvedValue([{}])
    renderPage()
    typeInto("Watch acme")
    fireEvent.click(screen.getByRole("button", { name: "Send, hold to think harder" }))
    const button = await screen.findByRole("button", { name: /Approve/ })
    expect(approve).not.toHaveBeenCalled()
    fireEvent.click(button)
    expect(await screen.findByRole("button", { name: /Done/ })).toBeTruthy()
    expect(approve).toHaveBeenCalledTimes(1)
  })
})

describe("mention detection and copy", () => {
  it("finds an @ only at the start of a word, before the caret", () => {
    expect(mentionAt("hello @gy", 9)).toEqual({ query: "gy", start: 6, end: 9 })
    expect(mentionAt("@", 1)).toEqual({ query: "", start: 0, end: 1 })
    expect(mentionAt("mail me at a@b.com", 18)).toBeNull()
    expect(mentionAt("hello @gy world", 15)).toBeNull()
  })

  it("has Arabic copy for every key, shortcut and mention type", () => {
    for (const key of Object.keys(AGENT_COPY.en)) expect(AGENT_COPY.ar[key], key).toBeTruthy()
    for (const key of Object.keys(AGENT_COPY.en.shortcuts)) expect(AGENT_COPY.ar.shortcuts[key].prompt, key).toBeTruthy()
    for (const key of Object.keys(AGENT_COPY.en.mentionTypes)) expect(AGENT_COPY.ar.mentionTypes[key], key).toBeTruthy()
  })
})
