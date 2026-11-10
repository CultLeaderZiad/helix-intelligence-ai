import { afterEach, beforeEach, expect, it, vi } from "vitest"

vi.mock("../sessionStore", () => ({ getAccessToken: () => null }))

import { request } from "../http"

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

it("normalizes FastAPI 422 validation arrays to a string message", async () => {
  fetchMock.mockResolvedValue({
    ok: false,
    status: 422,
    statusText: "Unprocessable Entity",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({
      detail: [{
        type: "value_error",
        loc: ["body", "email"],
        msg: "Invalid email address",
        input: "invalid",
      }],
    }),
  })

  const error = await request("/auth/sign-in", { method: "POST", body: {} }).catch((caught) => caught)

  expect(error).toMatchObject({ status: 422 })
  expect(typeof error.message).toBe("string")
  expect(error.message).toBe("Invalid email address")
})

it("uses a safe validation message for malformed structured 422 details", async () => {
  fetchMock.mockResolvedValue({
    ok: false,
    status: 422,
    statusText: "Unprocessable Entity",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({ detail: { message: { unexpected: true } } }),
  })

  const error = await request("/auth/sign-in", { method: "POST", body: {} }).catch((caught) => caught)

  expect(error).toMatchObject({ status: 422, message: "Validation error" })
  expect(typeof error.message).toBe("string")
})
