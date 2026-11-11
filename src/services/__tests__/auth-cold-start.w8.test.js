import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../http", () => {
  class ServiceError extends Error {
    /**
     * @param {string} message
     * @param {{ status?: number | null, code?: string }} [options]
     */
    constructor(message, { status = null, code = "service_error" } = {}) {
      super(message)
      this.name = "ServiceError"
      this.status = status
      this.code = code
    }
  }
  return { request: vi.fn(), ServiceError }
})

import { request as httpRequest } from "../http"
import authService, { resetAuthFlights, setAuthRecoveryOverridesForTests } from "../api/authService.api"
import { clearSession, getAccessToken } from "../sessionStore"
import { isColdStartFailure, waitUntilHealthy, withColdStartRetry } from "../coldStart"

const request = vi.mocked(httpRequest)
const fetchMock = vi.fn()

const sessionResponse = (id, token) => ({
  access_token: token,
  user_id: id,
  email: `${id}@example.test`,
  organization_id: `org-${id}`,
  role: "customer",
})

/** @param {string} code @param {number | null} [status] */
function failure(code, status = null) {
  return Object.assign(new Error(code), { code, status })
}

describe("sign-in cold start versus credential refusal", () => {
  beforeEach(() => {
    clearSession()
    resetAuthFlights()
    setAuthRecoveryOverridesForTests()
    request.mockReset()
    fetchMock.mockReset()
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    resetAuthFlights()
  })

  it("does not call health or retry when sign-in returns 401", async () => {
    request.mockRejectedValue(failure("http_401", 401))

    const error = await authService.signIn({ email: "owner@example.test", password: "wrong" }).catch((caught) => caught)

    expect(error).toMatchObject({ status: 401, code: "http_401" })
    expect(request).toHaveBeenCalledTimes(1)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(getAccessToken()).toBeNull()
  })

  it("does not call health or retry when sign-in returns 403", async () => {
    request.mockRejectedValue(failure("http_403", 403))

    const error = await authService.signIn({ email: "owner@example.test", password: "wrong" }).catch((caught) => caught)

    expect(error).toMatchObject({ status: 403 })
    expect(request).toHaveBeenCalledTimes(1)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("keeps a timed-out sign-in to one request until health is 200, then retries once", async () => {
    let attempts = 0
    /** @type {((value: unknown) => void) | null} */
    let releaseRetry = null
    request.mockImplementation(() => {
      attempts += 1
      if (attempts === 1) return Promise.reject(failure("request_timeout"))
      return new Promise((resolve) => {
        releaseRetry = resolve
      })
    })
    /** @type {((value: { ok: boolean, status: number }) => void) | null} */
    let releaseHealth = null
    fetchMock.mockImplementation(() => new Promise((resolve) => {
      releaseHealth = resolve
    }))

    const pending = authService.signIn({ email: "owner@example.test", password: "secret" })
    const joined = authService.signIn({ email: "owner@example.test", password: "secret" })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(attempts).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/health$/)

    releaseHealth?.({ ok: true, status: 200 })
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(attempts).toBe(2)

    releaseRetry?.(sessionResponse("owner", "woken-token"))
    const [first, second] = await Promise.all([pending, joined])

    expect(first.user.id).toBe("owner")
    expect(second.user.id).toBe("owner")
    expect(getAccessToken()).toBe("woken-token")
    expect(attempts).toBe(2)
  })

  it("surfaces a credential error from the single retry after the service wakes", async () => {
    request
      .mockRejectedValueOnce(failure("server_waking", 502))
      .mockRejectedValueOnce(failure("http_401", 401))
    fetchMock.mockResolvedValue({ ok: true, status: 200 })

    const error = await authService.signIn({ email: "owner@example.test", password: "wrong" }).catch((caught) => caught)

    expect(error).toMatchObject({ status: 401, code: "http_401" })
    expect(request).toHaveBeenCalledTimes(2)
    expect(getAccessToken()).toBeNull()
  })

  it("reports server unavailable when health never returns 200, without a second sign-in", async () => {
    let clock = 0
    setAuthRecoveryOverridesForTests({
      budgetMs: 90_000,
      now: () => clock,
      sleep: async (ms) => {
        clock += ms
      },
    })
    request.mockRejectedValue(failure("network_error"))
    fetchMock.mockResolvedValue({ ok: false, status: 503 })

    const error = await authService.signIn({ email: "owner@example.test", password: "secret" }).catch((caught) => caught)

    expect(error).toMatchObject({ code: "server_unavailable" })
    expect(error.status).not.toBe(401)
    expect(clock).toBeGreaterThanOrEqual(90_000)
    expect(request).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls.length).toBeGreaterThan(1)
    expect(getAccessToken()).toBeNull()
  })

  it("reports server unavailable when the retry also times out", async () => {
    request.mockRejectedValue(failure("request_timeout"))
    fetchMock.mockResolvedValue({ ok: true, status: 200 })

    const error = await authService.signIn({ email: "owner@example.test", password: "secret" }).catch((caught) => caught)

    expect(error).toMatchObject({ code: "server_unavailable" })
    expect(request).toHaveBeenCalledTimes(2)
  })

  it("applies the same one-retry recovery to sign-up", async () => {
    let signUps = 0
    request.mockImplementation((path) => {
      if (path === "/auth/sign-up") {
        signUps += 1
        if (signUps === 1) return Promise.reject(failure("http_504", 504))
        return Promise.resolve({ ok: true })
      }
      return Promise.resolve(sessionResponse("new-user", "new-token"))
    })
    fetchMock.mockResolvedValue({ ok: true, status: 200 })

    const result = await authService.signUp({
      name: "Owner",
      email: "new@example.test",
      password: "secret123",
    })

    expect(signUps).toBe(2)
    expect(request).toHaveBeenCalledTimes(3)
    expect(result.user.id).toBe("new-user")
    expect(getAccessToken()).toBe("new-token")
  })

  it("does not run the sign-in retry until the first attempt has settled", async () => {
    let active = 0
    let maxActive = 0
    let attempts = 0
    /** @type {number[]} */
    const starts = []

    await withColdStartRetry(async () => {
      attempts += 1
      starts.push(attempts)
      active += 1
      maxActive = Math.max(maxActive, active)
      await Promise.resolve()
      active -= 1
      if (attempts === 1) throw failure("request_timeout")
      return "signed-in"
    }, {
      fetchImpl: async () => ({ ok: true, status: 200 }),
      sleep: async () => {},
      now: () => 0,
    })

    expect(starts).toEqual([1, 2])
    expect(maxActive).toBe(1)
  })
})

describe("health wait budget", () => {
  it("stops polling at the budget and treats 502 as a reason to wait", async () => {
    let clock = 0
    let probes = 0
    const healthy = await waitUntilHealthy({
      budgetMs: 90_000,
      healthUrl: "https://helix-intelligence-ai.onrender.com/api/health",
      initialDelayMs: 1000,
      maxDelayMs: 8000,
      now: () => clock,
      sleep: async (ms) => {
        clock += ms
      },
      fetchImpl: async (url) => {
        probes += 1
        expect(url).toBe("https://helix-intelligence-ai.onrender.com/api/health")
        return { ok: false, status: 502 }
      },
    })

    expect(healthy).toBe(false)
    expect(clock).toBeGreaterThanOrEqual(90_000)
    expect(probes).toBeGreaterThan(1)
  })

  it("returns as soon as health is 200 and does not treat 401 as cold", async () => {
    expect(isColdStartFailure(failure("http_401", 401))).toBe(false)
    expect(isColdStartFailure(failure("request_timeout"))).toBe(true)
    expect(isColdStartFailure(failure("http_503", 503))).toBe(true)

    let probes = 0
    const healthy = await waitUntilHealthy({
      budgetMs: 90_000,
      now: () => 0,
      sleep: async () => {
        throw new Error("sleep should not run after a 200")
      },
      fetchImpl: async () => {
        probes += 1
        return { ok: true, status: 200 }
      },
    })

    expect(healthy).toBe(true)
    expect(probes).toBe(1)
  })
})
