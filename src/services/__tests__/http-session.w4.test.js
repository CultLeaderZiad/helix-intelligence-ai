import { afterEach, beforeEach, expect, it, vi } from "vitest"

const activeSession = vi.hoisted(() => ({ token: null }))
vi.mock("../sessionStore", () => ({ getAccessToken: () => activeSession.token }))

import { request } from "../http"

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  activeSession.token = null
  vi.useFakeTimers()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it("keeps the original account token across retries", async () => {
  activeSession.token = "account-a-token"
  fetchMock
    .mockImplementationOnce(async () => {
      activeSession.token = "account-b-token"
      throw new TypeError("offline")
    })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ok: true }) })

  const result = request("/private").then((value) => value)
  await vi.advanceTimersByTimeAsync(1100)

  expect(await result).toEqual({ ok: true })
  expect(fetchMock.mock.calls.map(([, options]) => options.headers.Authorization)).toEqual([
    "Bearer account-a-token",
    "Bearer account-a-token",
  ])
})

it("does not let a stale unauthorized response clear a newer session", async () => {
  activeSession.token = "account-a-token"
  const unauthorized = vi.fn()
  window.addEventListener("helix:unauthorized", unauthorized)
  fetchMock.mockImplementation(async (_url, options) => {
    expect(options.headers.Authorization).toBe("Bearer account-a-token")
    activeSession.token = "account-b-token"
    return {
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "Expired session" }),
    }
  })

  try {
    await expect(request("/private")).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).not.toHaveBeenCalled()
  } finally {
    window.removeEventListener("helix:unauthorized", unauthorized)
  }
})
