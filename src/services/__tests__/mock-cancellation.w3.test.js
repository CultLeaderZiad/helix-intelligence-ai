import { afterEach, beforeEach, expect, it, vi } from "vitest"
import discoverService from "../mock/discoverService.mock"
import mediaService from "../mock/mediaService.mock"
import { delay } from "../mock/latency"

beforeEach(() => vi.useFakeTimers())
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers() })

for (const [name, call] of [
  ["discovery search", signal => discoverService.search({}, { signal })],
  ["discovery poll", signal => discoverService.getJobStatus("unused", { signal })],
  ["discovery results", signal => discoverService.getJobResults("unused", {}, { signal })],
  ["media generation", signal => mediaService.generate({}, { signal })],
  ["media poll", signal => mediaService.getJob("unused", { signal })],
  ["media results", signal => mediaService.getJobResult("unused", { signal })],
  ["media cancellation", signal => mediaService.cancel("unused", { signal })],
]) {
  for (const preAborted of [true, false]) {
    it(`${name} rejects ${preAborted ? "before starting" : "during its wait"} with the abort reason and clears timers`, async () => {
      const controller = new AbortController()
      const reason = new DOMException("Stopped", "AbortError")
      if (preAborted) controller.abort(reason)
      const result = call(controller.signal).catch(error => error)
      if (!preAborted) {
        expect(vi.getTimerCount()).toBe(1)
        controller.abort(reason)
      }
      expect(await result).toBe(reason)
      expect(vi.getTimerCount()).toBe(0)
    })
  }
}

it("a successful mock delay removes its abort listener", async () => {
  const controller = new AbortController()
  const remove = vi.spyOn(controller.signal, "removeEventListener")
  const pending = delay(100, { signal: controller.signal })
  await vi.advanceTimersByTimeAsync(100)
  await pending
  expect(remove).toHaveBeenCalledWith("abort", expect.any(Function))
  expect(vi.getTimerCount()).toBe(0)
})

it("an aborted mock generation creates neither a job nor simulated worker timers", async () => {
  const controller = new AbortController()
  const randomUUID = vi.spyOn(crypto, "randomUUID")
  const pending = mediaService.generate({ prompt: "aborted" }, { signal: controller.signal }).catch(error => error)
  controller.abort()
  expect((await pending).name).toBe("AbortError")
  await vi.advanceTimersByTimeAsync(1000)
  expect(randomUUID).not.toHaveBeenCalled()
  expect(vi.getTimerCount()).toBe(0)
  randomUUID.mockRestore()
})
