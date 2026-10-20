// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const { mediaService, discoverService } = vi.hoisted(() => ({
  mediaService: { generate: vi.fn(), getJob: vi.fn(), getJobResult: vi.fn(), cancel: vi.fn() },
  discoverService: { search: vi.fn(), getJobStatus: vi.fn(), getJobResults: vi.fn(), cancelJob: vi.fn() },
}))
vi.mock("@/services", () => ({ mediaService, discoverService }))
import { useMediaGenerate } from "../useMediaGenerate"
import { useDiscoverySearch } from "../useDiscoverySearch"
import { JOB_POLL_TIMEOUT_MS } from "@/services/config"

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
let root, latest
function mount(hook) {
  const node = document.createElement("div")
  document.body.append(node)
  root = createRoot(node)
  function Harness() { latest = hook(); return null }
  act(() => root.render(<Harness />))
}
async function flush(fn = () => {}) { await act(async () => { fn(); await Promise.resolve() }) }
async function advance(ms) { await act(async () => { await vi.advanceTimersByTimeAsync(ms) }) }

beforeEach(() => {
  vi.useFakeTimers()
  vi.resetAllMocks()
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
})
afterEach(() => {
  act(() => root?.unmount())
  root = null
  document.body.replaceChildren()
  vi.useRealTimers()
})

for (const [name, hook, service, start, status, created] of [
  ["media", useMediaGenerate, mediaService, "generate", "getJob", id => ({ job_id: id })],
  ["discovery", useDiscoverySearch, discoverService, "search", "getJobStatus", id => ({ job_id: id })],
]) {
  describe(`${name} lifecycle`, () => {
    it("ignores out-of-order submissions, including reused backend IDs", async () => {
      const first = deferred(), second = deferred()
      service[start].mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
      service[status].mockReturnValue(new Promise(() => {}))
      mount(hook)
      await flush(() => { latest.submit({ query: "old" }); latest.submit({ query: "new" }) })
      await flush(() => second.resolve({ ...created("same"), marker: "new" }))
      await flush(() => first.resolve({ ...created("same"), marker: "old" }))
      expect(latest.job.marker).toBe("new")
      expect(service[start].mock.calls[0][1].signal.aborted).toBe(true)
    })

    it("ignores stale submission errors without clearing a newer deadline", async () => {
      const first = deferred(), second = deferred()
      service[start].mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
      mount(hook)
      await flush(() => { latest.submit({}); latest.submit({}) })
      await flush(() => first.reject(new Error("old failure")))
      expect(latest.phase).toBe("submitting")
      expect(latest.error).toBeNull()
      await advance(JOB_POLL_TIMEOUT_MS)
      expect(latest.isBusy).toBe(false)
      expect(vi.getTimerCount()).toBe(0)
    })

    it("an old poll on a reused job ID cannot publish state or schedule a timer", async () => {
      const stale = deferred(), fresh = deferred()
      service[start].mockResolvedValue(created("same"))
      service[status].mockReturnValueOnce(stale.promise).mockReturnValueOnce(fresh.promise)
      mount(hook)
      await flush(() => latest.submit({}))
      await advance(400)
      await flush(() => latest.submit({}))
      await advance(400)
      await flush(() => fresh.resolve({ status: "running", marker: "new" }))
      const timers = vi.getTimerCount()
      await flush(() => stale.resolve({ status: "running", marker: "old" }))
      expect(latest.job.marker).toBe("new")
      expect(vi.getTimerCount()).toBe(timers)
    })

    it("cancel invalidates a pending submission before it completes", async () => {
      const pending = deferred()
      service[start].mockReturnValue(pending.promise)
      mount(hook)
      await flush(() => latest.submit({}))
      await flush(() => latest.cancel())
      await flush(() => pending.resolve(created("late")))
      await advance(20000)
      expect(latest.phase).toBe("idle")
      expect(latest.job).toBeNull()
      expect(service[status]).not.toHaveBeenCalled()
      expect(vi.getTimerCount()).toBe(0)
    })

    it("unmount aborts a pending submission and never starts polling", async () => {
      const pending = deferred()
      service[start].mockReturnValue(pending.promise)
      mount(hook)
      await flush(() => latest.submit({}))
      const signal = service[start].mock.calls[0][1]?.signal
      act(() => root.unmount()); root = null
      await flush(() => pending.resolve(created("late")))
      await advance(20000)
      expect(signal?.aborted).toBe(true)
      expect(service[status]).not.toHaveBeenCalled()
      expect(vi.getTimerCount()).toBe(0)
    })

    it("enforces the overall deadline even when submission never settles", async () => {
      service[start].mockReturnValue(new Promise(() => {}))
      mount(hook)
      await flush(() => latest.submit({}))
      await advance(JOB_POLL_TIMEOUT_MS)
      expect(latest.isBusy).toBe(false)
      expect(service[start].mock.calls[0][1].signal.aborted).toBe(true)
      expect(vi.getTimerCount()).toBe(0)
    })

    it("bounds polling and requests server cancellation at the discovery deadline", async () => {
      service[start].mockResolvedValue(created("job"))
      service[status].mockResolvedValue({ job_id: "job", status: "running" })
      mount(hook)
      await flush(() => latest.submit({}))
      await advance(JOB_POLL_TIMEOUT_MS)
      const calls = service[status].mock.calls.length
      expect(calls).toBeGreaterThan(1)
      expect(calls).toBeLessThan(80)
      if (name === "discovery") {
        expect(service.cancelJob).toHaveBeenCalledWith("job")
        expect(latest.phase).toBe("cancelling")
        expect(latest.isBusy).toBe(true)
      } else {
        expect(latest.isBusy).toBe(false)
        expect(vi.getTimerCount()).toBe(0)
        await advance(JOB_POLL_TIMEOUT_MS)
        expect(service[status]).toHaveBeenCalledTimes(calls)
      }
    })
  })
}

for (const [name, hook, service, start, status, resultMethod] of [
  ["media", useMediaGenerate, mediaService, "generate", "getJob", "getJobResult"],
  ["discovery", useDiscoverySearch, discoverService, "search", "getJobStatus", "getJobResults"],
]) {
  it(`${name} keeps the submission deadline through a hung result fetch`, async () => {
    service[start].mockResolvedValue({ job_id: "job" })
    service[status].mockResolvedValue({ status: "succeeded" })
    const pending = deferred()
    service[resultMethod].mockReturnValue(pending.promise)
    mount(hook)
    await flush(() => latest.submit({}))
    await advance(400)
    expect(latest.phase).toBe("fetching_results")
    await advance(JOB_POLL_TIMEOUT_MS - 400)
    expect(latest.isBusy).toBe(false)
    const phase = latest.phase
    await flush(() => pending.resolve({ items: ["late"], url: "late.png" }))
    expect(latest.phase).toBe(phase)
    expect(vi.getTimerCount()).toBe(0)
  })

  it(`${name} result completion after unmount creates no timers`, async () => {
    service[start].mockResolvedValue({ job_id: "job" })
    service[status].mockResolvedValue({ status: "succeeded" })
    const pending = deferred()
    service[resultMethod].mockReturnValue(pending.promise)
    mount(hook)
    await flush(() => latest.submit({}))
    await advance(400)
    act(() => root.unmount()); root = null
    await flush(() => pending.reject(new Error("late result failure")))
    expect(vi.getTimerCount()).toBe(0)
  })
}

it("slow server cancellation cannot reset a resubmitted generation", async () => {
  mediaService.generate.mockResolvedValueOnce({ job_id: "old" }).mockResolvedValueOnce({ job_id: "new" })
  mediaService.getJob.mockReturnValue(new Promise(() => {}))
  const cancellation = deferred()
  mediaService.cancel.mockReturnValue(cancellation.promise)
  mount(useMediaGenerate)
  await flush(() => latest.submit({}))
  await flush(() => latest.cancel())
  await flush(() => latest.submit({}))
  await flush(() => cancellation.resolve())
  expect(latest.phase).toBe("running")
  expect(latest.job.job_id).toBe("new")
})

it("late media result errors cannot overwrite a canceled/new generation", async () => {
  const result = deferred()
  mediaService.generate.mockResolvedValue({ job_id: "old" })
  mediaService.getJob.mockResolvedValue({ status: "succeeded", result_url: "old.png" })
  mediaService.getJobResult.mockReturnValue(result.promise)
  mount(useMediaGenerate)
  await flush(() => latest.submit({}))
  await flush(() => latest.cancel())
  await flush(() => result.reject(new Error("late")))
  expect(latest.phase).toBe("idle")
  expect(latest.result).toBeNull()
  expect(vi.getTimerCount()).toBe(0)
})

it("late discovery pagination cannot replace a newer sort on the same job", async () => {
  discoverService.search.mockResolvedValue({ job_id: "job" })
  discoverService.getJobStatus.mockResolvedValue({ status: "succeeded" })
  discoverService.getJobResults.mockResolvedValueOnce({ items: ["initial"] })
  mount(useDiscoverySearch)
  await flush(() => latest.submit({}))
  await advance(400)
  const old = deferred(), next = deferred()
  discoverService.getJobResults.mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise)
  await flush(() => { latest.refine({ sort: "old" }); latest.refine({ sort: "new" }) })
  await flush(() => next.resolve({ items: ["new"] }))
  await flush(() => old.resolve({ items: ["old"] }))
  expect(latest.results.items).toEqual(["new"])
})
