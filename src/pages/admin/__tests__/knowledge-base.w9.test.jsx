import React from "react"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { adminService } from "@/services"
import { KnowledgeBasePage } from "../KnowledgeBasePage"

describe("Admin knowledge base page", () => {
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
})
