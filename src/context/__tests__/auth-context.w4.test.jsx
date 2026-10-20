import { StrictMode } from "react"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { AuthProvider, useAuth } from "../AuthContext"

const { service } = vi.hoisted(() => ({
  service: {
    getStoredToken: vi.fn(() => "cached-token"),
    getSession: vi.fn(() => Promise.resolve(null)),
    signOut: vi.fn(),
  },
}))
vi.mock("@/services", () => ({ authService: service }))
vi.mock("@/services/sessionStore", () => ({
  getAccessToken: () => "cached-token",
  getCachedUser: () => null,
}))

function SessionState() {
  const { user, status } = useAuth()
  return <output>{`${status}:${user?.id ?? "none"}`}</output>
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("W4 session resolution in StrictMode", () => {
  it.each(["empty", "rejected"])("settles an %s session without nested state updates", async (result) => {
    if (result === "rejected") service.getSession.mockRejectedValue(new Error("offline"))
    else service.getSession.mockResolvedValue(null)
    render(<StrictMode><AuthProvider><SessionState /></AuthProvider></StrictMode>)
    await waitFor(() => expect(screen.getByRole("status").textContent).toBe("unauthenticated:none"))
  })
})
