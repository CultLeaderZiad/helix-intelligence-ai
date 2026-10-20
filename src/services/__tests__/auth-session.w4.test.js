import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../http", () => ({
  request: vi.fn(),
  ServiceError: class ServiceError extends Error {
    constructor(message, { code = "service_error" } = {}) {
      super(message)
      this.code = code
    }
  },
}))

import { request } from "../http"
import { authService } from "../api/authService.api"
import {
  clearSession,
  getAccessToken,
  getCachedUser,
  setAccessToken,
  setCachedUser,
} from "../sessionStore"

const sessionResponse = (id, token) => ({
  access_token: token,
  user_id: id,
  email: `${id}@example.test`,
  organization_id: `org-${id}`,
  role: "customer",
})

describe("auth session transitions", () => {
  beforeEach(() => {
    clearSession()
    request.mockReset()
  })

  it("replaces a prior account without retaining its profile", async () => {
    setAccessToken("old-token")
    setCachedUser({ id: "old-user", organization_id: "org-old-user" })
    const cleared = vi.fn()
    window.addEventListener("helix:session-clearing", cleared)
    request.mockResolvedValue(sessionResponse("new-user", "new-token"))

    try {
      const result = await authService.signIn({ email: "new@example.test", password: "secret" })

      expect(result.user.id).toBe("new-user")
      expect(getAccessToken()).toBe("new-token")
      expect(getCachedUser()).toMatchObject({ id: "new-user", organization_id: "org-new-user" })
      expect(cleared).toHaveBeenCalledOnce()
    } finally {
      window.removeEventListener("helix:session-clearing", cleared)
    }
  })

  it("clears the admin identity before activating an impersonation token", () => {
    setAccessToken("admin-token")
    setCachedUser({ id: "admin", role: "admin" })
    const cleared = vi.fn()
    window.addEventListener("helix:session-clearing", cleared)

    try {
      authService.switchToImpersonatedSession("target-token")

      expect(getAccessToken()).toBe("target-token")
      expect(getCachedUser()).toBeNull()
      expect(cleared).toHaveBeenCalledOnce()
    } finally {
      window.removeEventListener("helix:session-clearing", cleared)
    }
  })

  it("clears local session state when sign-out transport fails", async () => {
    setAccessToken("active-token")
    setCachedUser({ id: "active-user" })
    request.mockRejectedValue(new Error("offline"))

    await authService.signOut()

    expect(getAccessToken()).toBeNull()
    expect(getCachedUser()).toBeNull()
  })
})
