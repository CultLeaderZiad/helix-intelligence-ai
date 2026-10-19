import { afterEach, beforeEach, expect, it, vi } from "vitest"
vi.mock("../sessionStore", () => ({ getAccessToken: () => null }))
import { request } from "../http"

beforeEach(() => { vi.useFakeTimers(); vi.stubGlobal("fetch", vi.fn()) })
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

it("aborts during network retry backoff without another fetch or timer", async () => {
  fetch.mockRejectedValue(new TypeError("offline"))
  const controller = new AbortController()
  const promise = request("/test", { signal: controller.signal })
  const caught = promise.catch(error => error)
  await vi.advanceTimersByTimeAsync(0)
  expect(fetch).toHaveBeenCalledTimes(1)
  controller.abort()
  expect((await caught).name).toBe("AbortError")
  await vi.advanceTimersByTimeAsync(60000)
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(vi.getTimerCount()).toBe(0)
})

it("aborts during gateway retry backoff and removes timers", async () => {
  fetch.mockResolvedValue({ ok: false, status: 503, headers: new Headers() })
  const controller = new AbortController()
  const promise = request("/test", { signal: controller.signal }).catch(error => error)
  await vi.advanceTimersByTimeAsync(0)
  controller.abort()
  expect((await promise).name).toBe("AbortError")
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(vi.getTimerCount()).toBe(0)
})

it("uses one overall deadline across retries, not a fresh deadline per fetch", async () => {
  fetch.mockRejectedValue(new TypeError("offline"))
  const result = request("/test", { timeoutMs: 1500 }).catch(error => error)
  await vi.advanceTimersByTimeAsync(1500)
  expect((await result).code).toBe("request_timeout")
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(vi.getTimerCount()).toBe(0)
})

it("deadline aborts an in-flight fetch", async () => {
  let signal
  fetch.mockImplementation((url, options) => new Promise((resolve, reject) => {
    signal = options.signal
    signal.addEventListener("abort", () => reject(signal.reason), { once: true })
  }))
  const result = request("/test", { timeoutMs: 2500 }).catch(error => error)
  await vi.advanceTimersByTimeAsync(2500)
  expect((await result).code).toBe("request_timeout")
  expect(signal.aborted).toBe(true)
  expect(vi.getTimerCount()).toBe(0)
})

it("does not retry mutations without an idempotency key", async () => {
  fetch.mockRejectedValue(new TypeError("offline"))
  const error = await request("/test", { method: "POST", body: {} }).catch(error => error)
  expect(error.code).toBe("network_error")
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(vi.getTimerCount()).toBe(0)
})

it("pre-aborted calls never reach fetch", async () => {
  const controller = new AbortController()
  controller.abort()
  const error = await request("/test", { signal: controller.signal }).catch(error => error)
  expect(error.name).toBe("AbortError")
  expect(fetch).not.toHaveBeenCalled()
  expect(vi.getTimerCount()).toBe(0)
})

it("retries key-protected mutations but stops after the bounded retry count", async () => {
  fetch.mockRejectedValue(new TypeError("offline"))
  const result = request("/test", { method: "POST", headers: { "Idempotency-Key": "test-key" } }).catch(error => error)
  await vi.runAllTimersAsync()
  expect((await result).code).toBe("network_error")
  expect(fetch).toHaveBeenCalledTimes(7)
  expect(vi.getTimerCount()).toBe(0)
})

it("success removes the caller abort listener and request deadline", async () => {
  fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ done: true }) })
  const controller = new AbortController()
  const remove = vi.spyOn(controller.signal, "removeEventListener")
  expect(await request("/test", { signal: controller.signal })).toEqual({ done: true })
  expect(remove).toHaveBeenCalledWith("abort", expect.any(Function))
  expect(vi.getTimerCount()).toBe(0)
})

it("structured 503 errors are not retried", async () => {
  fetch.mockResolvedValue({
    ok: false, status: 503, statusText: "Unavailable",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({ detail: { code: "worker_offline", message: "offline" } }),
  })
  const error = await request("/test").catch(error => error)
  expect(error.code).toBe("worker_offline")
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(vi.getTimerCount()).toBe(0)
})
