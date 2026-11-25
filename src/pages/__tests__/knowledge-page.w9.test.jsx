import React from "react"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "@/context/LanguageContext"
import * as http from "@/services/http"
import { KNOWLEDGE_COPY, KnowledgePage } from "../KnowledgePage"

const renderPage = () => render(<LanguageProvider><KnowledgePage /></LanguageProvider>)

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.setItem("helix_lang", "en")
})
afterEach(cleanup)

describe("Knowledge base (read-only for every signed-in user)", () => {
  it("lists the articles and opens one", async () => {
    const calls = []
    vi.spyOn(http, "request").mockImplementation(async (path) => {
      calls.push(path)
      if (path === "/knowledge-base") return { items: [{ id: "a1", title: "Pricing guide", version: 2, updated_at: "2026-11-20T00:00:00Z" }] }
      return { id: "a1", title: "Pricing guide", version: 2, updated_at: "2026-11-20T00:00:00Z", text: "How plans work" }
    })
    renderPage()
    fireEvent.click(await screen.findByText("Pricing guide"))
    expect(await screen.findByText("How plans work")).toBeTruthy()
    expect(calls).toEqual(["/knowledge-base", "/knowledge-base/a1"])
  })

  it("never calls an admin or write endpoint", async () => {
    const spy = vi.spyOn(http, "request").mockResolvedValue({ items: [] })
    renderPage()
    await waitFor(() => expect(spy).toHaveBeenCalled())
    for (const [path, options] of spy.mock.calls) {
      expect(path).not.toMatch(/admin/)
      expect(options?.method ?? "GET").toBe("GET")
    }
  })

  it("has Arabic copy for every string", () => {
    for (const key of Object.keys(KNOWLEDGE_COPY.en)) expect(KNOWLEDGE_COPY.ar[key], key).toBeTruthy()
  })
})
