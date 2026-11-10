import { beforeEach, describe, expect, it, vi } from "vitest"

const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }))

vi.mock("../http", () => ({
  request: requestMock,
  ServiceError: class ServiceError extends Error {
    constructor(message, options = {}) {
      super(message)
      Object.assign(this, options)
    }
  },
}))

import authService from "../api/authService.api"

describe("server-side onboarding auth methods", () => {
  beforeEach(() => requestMock.mockReset())

  it("persists completion and restart through the authenticated session routes", async () => {
    requestMock.mockResolvedValue({ message: "ok" })

    await authService.completeOnboarding()
    await authService.restartOnboarding()

    expect(requestMock).toHaveBeenNthCalledWith(1, "/auth/session/onboarding/complete", {
      method: "POST",
    })
    expect(requestMock).toHaveBeenNthCalledWith(2, "/auth/session/onboarding/restart", {
      method: "POST",
    })
  })
})
