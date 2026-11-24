import React from "react"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { adminService } from "@/services"
import { KnowledgeBasePage } from "../KnowledgeBasePage"

describe("Admin knowledge base page", () => {
  afterEach(cleanup)
  beforeEach(() => vi.restoreAllMocks())

  it("lists documents and the audit log from the server", async () => {
    vi.spyOn(adminService, "listKnowledgeBase").mockResolvedValue({
      items: [{ id: "d1", title: "Ad playbook", version: 2, status: "enabled", chunks: 4, size_bytes: 2048 }],
    })
    vi.spyOn(adminService, "knowledgeBaseAudit").mockResolvedValue({
      items: [{ id: "a1", created_at: "2026-11-24", actor_id: "u1", action: "upload", title: "Ad playbook", version: 2 }],
    })
    render(<KnowledgeBasePage />)
    expect((await screen.findAllByText("Ad playbook")).length).toBe(2)
    expect(screen.getByText("v2")).toBeTruthy()
    expect(screen.getByText(/upload/)).toBeTruthy()
  })

  it("shows the error when loading fails (e.g. not a full admin)", async () => {
    vi.spyOn(adminService, "listKnowledgeBase").mockRejectedValue(new Error("Forbidden"))
    vi.spyOn(adminService, "knowledgeBaseAudit").mockRejectedValue(new Error("Forbidden"))
    render(<KnowledgeBasePage />)
    expect((await screen.findByRole("alert")).textContent).toBe("Forbidden")
  })

  const empty = () => {
    vi.spyOn(adminService, "listKnowledgeBase").mockResolvedValue({ items: [] })
    vi.spyOn(adminService, "knowledgeBaseAudit").mockResolvedValue({ items: [] })
  }

  it("sends chosen files and a zip to the server, not their text, and lists what was skipped", async () => {
    empty()
    const upload = vi.spyOn(adminService, "uploadKnowledgeFiles").mockResolvedValue({
      created: [{ id: "d1", title: "Hooks", version: 1, chunks: 3 }, { id: "d2", title: "Offers", version: 1, chunks: 2 }],
      skipped: [{ name: "kb.zip/README.md", reason: "README (describes the folder, not a subject)" }],
    })
    const { container } = render(<KnowledgeBasePage />)
    await screen.findByText("No documents yet.")
    const zip = new File(["PK"], "helix-kb.zip", { type: "application/zip" })
    fireEvent.change(container.querySelector('input[type="file"]'), { target: { files: [zip] } })
    expect(screen.getByText(/1 file selected: helix-kb.zip/)).toBeTruthy()
    // With a file chosen, nothing else is required: the upload is not blocked by an empty text box.
    expect(screen.queryByText("Or paste text")).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Upload" }))
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1))
    expect(upload.mock.calls[0][0]).toEqual([zip])
    expect(await screen.findByText(/2 documents added, 1 skipped/)).toBeTruthy()
    expect(screen.getAllByText(/README/).length).toBeGreaterThan(0)
  })

  it("shows the server's reason when an upload is refused", async () => {
    empty()
    vi.spyOn(adminService, "uploadKnowledgeFiles").mockRejectedValue(new Error("The archive has 400 files; the limit is 300."))
    const { container } = render(<KnowledgeBasePage />)
    await screen.findByText("No documents yet.")
    fireEvent.change(container.querySelector('input[type="file"]'), { target: { files: [new File(["x"], "big.zip")] } })
    fireEvent.click(screen.getByRole("button", { name: "Upload" }))
    expect((await screen.findByRole("alert")).textContent).toBe("The archive has 400 files; the limit is 300.")
  })

  it("still accepts pasted text when no file is chosen", async () => {
    empty()
    const paste = vi.spyOn(adminService, "uploadKnowledgeDocument").mockResolvedValue({ id: "d3", title: "Notes", version: 1, chunks: 1 })
    render(<KnowledgeBasePage />)
    await screen.findByText("No documents yet.")
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: "Notes" } })
    fireEvent.change(screen.getByLabelText(/Or paste text/), { target: { value: "Measure your own baseline." } })
    fireEvent.click(screen.getByRole("button", { name: "Upload" }))
    await waitFor(() => expect(paste).toHaveBeenCalledWith({ title: "Notes", text: "Measure your own baseline." }))
  })
})
