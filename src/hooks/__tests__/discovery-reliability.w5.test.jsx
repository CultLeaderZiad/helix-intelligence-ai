// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const { discoverService } = vi.hoisted(() => ({
  discoverService: {
    search: vi.fn(),
    getJobStatus: vi.fn(),
    getJobResults: vi.fn(),
    cancelJob: vi.fn(),
  },
}))
vi.mock("@/services", () => ({ discoverService }))

import { PHASE, useDiscoverySearch } from "../useDiscoverySearch"
import { JOB_POLL_TIMEOUT_MS } from "@/services/config"

/**
 * @template T
 * @returns {{promise: Promise<T>, resolve: (value: T | PromiseLike<T>) => void}}
 */
function deferred() {
  /** @type {(value: T | PromiseLike<T>) => void} */
  let resolve = () => {}
  const promise = new Promise(yes => { resolve = yes })
  return { promise, resolve }
}

let root, latest, originalVisibility
function mount() {
  const node = document.createElement("div")
  document.body.append(node)
  root = createRoot(node)
  function Harness() { latest = useDiscoverySearch(); return null }
  act(() => root.render(<Harness />))
}

async function flush(fn = () => {}) {
  await act(async () => {
    fn()
    for (let index = 0; index < 6; index += 1) await Promise.resolve()
  })
}

async function advance(ms) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms) })
}

function setToken(value) {
  if (value) localStorage.setItem("helix_access_token", value)
  else localStorage.removeItem("helix_access_token")
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.resetAllMocks()
  setToken("owner-token")
  originalVisibility = Object.getOwnPropertyDescriptor(document, "visibilityState")
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => "visible",
  })
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
})

afterEach(() => {
  act(() => root?.unmount())
  root = null
  document.body.replaceChildren()
  localStorage.removeItem("helix_access_token")
  if (originalVisibility) {
    Object.defineProperty(document, "visibilityState", originalVisibility)
  } else {
    Reflect.deleteProperty(document, "visibilityState")
  }
  vi.useRealTimers()
})

describe("Discover server cancellation", () => {
  it("waits for a terminal server state instead of resetting local state", async () => {
    discoverService.search.mockResolvedValue({ job_id: "job-1", status: "running" })
    discoverService.getJobStatus
      .mockResolvedValueOnce({ job_id: "job-1", status: "running", stage_label: "Reading Meta library" })
      .mockResolvedValueOnce({ job_id: "job-1", status: "cancelled", stage_label: "Cancelled" })
    discoverService.cancelJob.mockResolvedValue({ job_id: "job-1", status: "cancelling" })
    mount()

    await flush(() => latest.submit({ query: "nike.com" }))
    await flush(() => latest.cancel())

    expect(discoverService.cancelJob).toHaveBeenCalledTimes(1)
    expect(discoverService.cancelJob).toHaveBeenCalledWith("job-1")
    expect(discoverService.cancelJob.mock.calls[0]).toHaveLength(1)
    expect(latest.phase).toBe(PHASE.CANCELLING)
    expect(latest.job.status).toBe("running")
    expect(latest.isBusy).toBe(true)

    await advance(600)
    expect(latest.phase).toBe(PHASE.CANCELLED)
    expect(latest.job.status).toBe("cancelled")
    expect(latest.isBusy).toBe(false)
  })

  it("keeps a failed cancellation visible and retryable", async () => {
    discoverService.search.mockResolvedValue({ job_id: "job-2", status: "running" })
    discoverService.getJobStatus.mockResolvedValue({ job_id: "job-2", status: "running" })
    discoverService.cancelJob
      .mockRejectedValueOnce(new Error("connection failed"))
      .mockResolvedValueOnce({ job_id: "job-2", status: "cancelled" })
    mount()

    await flush(() => latest.submit({ query: "adidas.com" }))
    await flush(() => latest.cancel())

    expect(latest.phase).toBe(PHASE.CANCEL_ERROR)
    expect(latest.cancelError).toBeInstanceOf(Error)
    expect(latest.job.job_id).toBe("job-2")
    expect(latest.isBusy).toBe(true)

    await flush(() => latest.cancel())
    expect(discoverService.cancelJob).toHaveBeenCalledTimes(2)
    expect(latest.phase).toBe(PHASE.CANCELLED)
    expect(latest.cancelError).toBeNull()
  })

  it("sends timeout cancellation without the aborted polling signal", async () => {
    discoverService.search.mockResolvedValue({ job_id: "job-3", status: "running" })
    discoverService.getJobStatus.mockResolvedValue({ job_id: "job-3", status: "running" })
    discoverService.cancelJob.mockRejectedValue(new Error("offline"))
    mount()

    await flush(() => latest.submit({ query: "example.com" }))
    await advance(JOB_POLL_TIMEOUT_MS)

    expect(discoverService.cancelJob).toHaveBeenCalledWith("job-3")
    expect(discoverService.cancelJob.mock.calls[0]).toHaveLength(1)
    expect(latest.phase).toBe(PHASE.CANCEL_ERROR)
    expect(latest.cancelError).toBeInstanceOf(Error)
    expect(latest.job.job_id).toBe("job-3")
    expect(latest.isBusy).toBe(true)
  })

  it("deduplicates polling while hidden and resumes once visible", async () => {
    const status = deferred()
    let visibility = "visible"
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => visibility,
    })
    discoverService.search.mockResolvedValue({ job_id: "job-4", status: "running" })
    discoverService.getJobStatus.mockReturnValue(status.promise)
    mount()

    await flush(() => latest.submit({ query: "store.example" }))
    visibility = "hidden"
    await advance(400)
    expect(discoverService.getJobStatus).not.toHaveBeenCalled()

    visibility = "visible"
    await flush(() => document.dispatchEvent(new Event("visibilitychange")))
    await flush(() => document.dispatchEvent(new Event("visibilitychange")))
    expect(discoverService.getJobStatus).toHaveBeenCalledTimes(1)

    await flush(() => status.resolve({ job_id: "job-4", status: "running" }))
    expect(discoverService.getJobStatus).toHaveBeenCalledTimes(1)
  })

  it("never sends cancellation using a different signed-in session", async () => {
    discoverService.search.mockResolvedValue({ job_id: "job-5", status: "running" })
    discoverService.getJobStatus.mockResolvedValue({ job_id: "job-5", status: "running" })
    mount()

    await flush(() => latest.submit({ query: "nike.com" }))
    setToken("different-session")
    await flush(() => latest.cancel())

    expect(discoverService.cancelJob).not.toHaveBeenCalled()
    expect(latest.phase).toBe(PHASE.CANCEL_ERROR)
    expect(latest.job.job_id).toBe("job-5")
  })

  it("does not cancel an unmounted job after the session changes", async () => {
    discoverService.search.mockResolvedValue({ job_id: "job-6", status: "running" })
    discoverService.getJobStatus.mockReturnValue(new Promise(() => {}))
    mount()

    await flush(() => latest.submit({ query: "nike.com" }))
    setToken("different-session")
    await flush(() => {
      act(() => root.unmount())
      root = null
    })

    expect(discoverService.cancelJob).not.toHaveBeenCalled()
  })
})
