import React from "react"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import agentService from "@/services/api/agentService.api"
import { HISTORY_COPY } from "../historyCopy"
import { ConversationHistory } from "../ConversationHistory"

const c = HISTORY_COPY.en
const ITEMS = [
  { id: "c1", title: "Gym shoes ideas", pinned: false, archived: false, updated_at: "2026-11-20T10:00:00Z" },
  { id: "c2", title: "Competitor X", pinned: true, archived: false, updated_at: "2026-11-21T10:00:00Z" },
]

function setup(props = {}) {
  const handlers = { onOpen: vi.fn(), onNew: vi.fn(), onRemoved: vi.fn() }
  render(<ConversationHistory c={c} lang="en" activeId="c1" refreshKey={0} {...handlers} {...props} />)
  return handlers
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(agentService, "conversations").mockResolvedValue({ items: ITEMS, max_active: 50 })
})
afterEach(cleanup)

describe("Ask Helix saved conversations", () => {
  it("has Arabic copy for every history string", () => {
    for (const key of Object.keys(HISTORY_COPY.en)) expect(HISTORY_COPY.ar[key], key).toBeTruthy()
  })

  it("lists the saved chats and tells the user nothing is deleted when the list fills", async () => {
    setup()
    expect(await screen.findByText("Gym shoes ideas")).toBeTruthy()
    expect(screen.getByText(/archived, not deleted/)).toBeTruthy()
  })

  it("opens a chat by loading its messages from the server", async () => {
    const conversation = { id: "c1", messages: [{ id: "m1", role: "user", content: "hi" }] }
    vi.spyOn(agentService, "conversation").mockResolvedValue(conversation)
    const { onOpen } = setup()
    fireEvent.click(await screen.findByText("Gym shoes ideas"))
    await waitFor(() => expect(onOpen).toHaveBeenCalledWith(conversation))
  })

  it("deletes only after a second press", async () => {
    const del = vi.spyOn(agentService, "deleteConversation").mockResolvedValue({ deleted: "c1" })
    const { onRemoved } = setup()
    await screen.findByText("Gym shoes ideas")
    const [first] = screen.getAllByRole("button", { name: c.remove })
    fireEvent.click(first)
    expect(del).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole("button", { name: c.confirmRemove }))
    await waitFor(() => expect(del).toHaveBeenCalledWith("c1"))
    expect(onRemoved).toHaveBeenCalled()
  })

  it("pins and archives through the server, and starts a new chat", async () => {
    const update = vi.spyOn(agentService, "updateConversation").mockResolvedValue({})
    const { onNew } = setup()
    await screen.findByText("Gym shoes ideas")
    fireEvent.click(screen.getAllByRole("button", { name: c.pin })[0])
    await waitFor(() => expect(update).toHaveBeenCalledWith("c1", { pinned: true }))
    fireEvent.click(screen.getAllByRole("button", { name: c.archive })[0])
    await waitFor(() => expect(update).toHaveBeenCalledWith("c1", { archived: true }))
    fireEvent.click(screen.getByRole("button", { name: new RegExp(c.newChat) }))
    expect(onNew).toHaveBeenCalled()
  })
})
