import { afterEach, beforeEach, expect, it, vi } from "vitest"

const { session } = vi.hoisted(() => ({ session: { token: null } }))
vi.mock("../sessionStore", () => ({ getAccessToken: () => session.token }))
import { request } from "../http"

const fetchMock = vi.fn()

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => data,
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  session.token = null
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it("coalesces concurrent identical GETs into one fetch", async () => {
  let resolveFetch
  fetchMock.mockImplementation(() => new Promise(resolve => { resolveFetch = resolve }))

  const first = request("/read")
  const second = request("/read")
  expect(fetchMock).toHaveBeenCalledTimes(1)

  resolveFetch(jsonResponse({ value: "shared" }))
  await expect(Promise.all([first, second])).resolves.toEqual([
    { value: "shared" },
    { value: "shared" },
  ])
})

it("shares a retry and removes successful entries before later calls", async () => {
  fetchMock.mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(jsonResponse({ value: "retried" }))
    .mockResolvedValueOnce(jsonResponse({ value: "fresh" }))

  const first = request("/retry", { timeoutMs: 5000 })
  const second = request("/retry", { timeoutMs: 5000 })
  expect(fetchMock).toHaveBeenCalledTimes(1)
  await vi.advanceTimersByTimeAsync(1000)
  await expect(Promise.all([first, second])).resolves.toEqual([
    { value: "retried" },
    { value: "retried" },
  ])
  await expect(request("/retry", { timeoutMs: 5000 })).resolves.toEqual({ value: "fresh" })
  expect(fetchMock).toHaveBeenCalledTimes(3)
})

it("removes rejected entries so a later GET can retry", async () => {
  fetchMock.mockResolvedValueOnce({
    ...jsonResponse({ detail: "rejected" }, 400),
  }).mockResolvedValueOnce(jsonResponse({ value: "recovered" }))

  await expect(request("/retry-after-error")).rejects.toMatchObject({ status: 400 })
  await expect(request("/retry-after-error")).resolves.toEqual({ value: "recovered" })
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

it("does not share reads across different auth, header, or deadline scopes", async () => {
  const responses = []
  fetchMock.mockImplementation(() => new Promise(resolve => { responses.push(resolve) }))

  session.token = "session-one"
  const first = request("/scoped", { headers: { "X-View": "one" }, timeoutMs: 5000 })
  session.token = "session-two"
  const second = request("/scoped", { headers: { "X-View": "one" }, timeoutMs: 5000 })
  const third = request("/scoped", { headers: { "X-View": "two" }, timeoutMs: 5000 })
  const fourth = request("/scoped", { headers: { "X-View": "one" }, timeoutMs: 6000 })

  expect(fetchMock).toHaveBeenCalledTimes(4)
  expect(fetchMock.mock.calls.map(([, options]) => options.headers.Authorization)).toEqual([
    "Bearer session-one",
    "Bearer session-two",
    "Bearer session-two",
    "Bearer session-two",
  ])
  responses.forEach(resolve => resolve(jsonResponse({ value: "ok" })))
  await Promise.all([first, second, third, fourth])
})

it("keeps caller-signalled GETs independent when one caller aborts", async () => {
  const pending = []
  fetchMock.mockImplementation((_url, { signal }) => new Promise((resolve, reject) => {
    pending.push({ resolve, signal })
    signal.addEventListener("abort", () => reject(signal.reason), { once: true })
  }))
  const firstController = new AbortController()
  const secondController = new AbortController()

  const first = request("/cancel-sensitive", { signal: firstController.signal })
  const second = request("/cancel-sensitive", { signal: secondController.signal })
  expect(fetchMock).toHaveBeenCalledTimes(2)

  firstController.abort()
  await expect(first).rejects.toHaveProperty("name", "AbortError")
  pending[1].resolve(jsonResponse({ value: "not cancelled" }))
  await expect(second).resolves.toEqual({ value: "not cancelled" })
})

it("never coalesces mutations", async () => {
  fetchMock.mockResolvedValue(jsonResponse({ value: "written" }))

  const first = request("/write", { method: "POST", body: { value: 1 } })
  const second = request("/write", { method: "POST", body: { value: 1 } })
  expect(fetchMock).toHaveBeenCalledTimes(2)
  await expect(Promise.all([first, second])).resolves.toEqual([
    { value: "written" },
    { value: "written" },
  ])
})
