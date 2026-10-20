// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom"
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

// Only the transport is controlled: the hooks, service selector, API adapters and
// request/retry implementation are real. A pending fetch rejects only when its
// actual fetch options.signal receives an abort event, not when the hook fences state.
const nativeFetch = globalThis.fetch
const fetchMock = vi.fn()
let useDiscoverySearch, useMediaGenerate
beforeAll(async () => {
  vi.useFakeTimers()
  vi.stubGlobal("fetch", fetchMock.mockImplementation(async () => response({})))
  ;({ useDiscoverySearch } = await import("../useDiscoverySearch"))
  ;({ useMediaGenerate } = await import("../useMediaGenerate"))
  // The unrelated module-level health keepalive is not part of a job lifecycle.
  vi.clearAllTimers()
})

const response = payload => ({ ok: true, status: 200, json: async () => payload })
let root, latest, navigate, node, pending
function mount(hook) {
  node = document.createElement("div")
  document.body.append(node)
  root = createRoot(node)
  function Feature() {
    latest = hook()
    navigate = useNavigate()
    return <output>{latest.phase}</output>
  }
  act(() => root.render(
    <MemoryRouter initialEntries={["/feature"]}>
      <Routes>
        <Route path="/feature" element={<Feature />} />
        <Route path="/away" element={<p>Another page</p>} />
      </Routes>
    </MemoryRouter>,
  ))
}
async function flush(fn = () => {}) {
  await act(async () => { fn(); await Promise.resolve() })
}
async function advance(ms) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms) })
}
function hangingFetch(options) {
  const request = { signal: options.signal, aborted: false }
  pending.push(request)
  return new Promise((resolve, reject) => {
    request.resolve = payload => resolve(response(payload))
    const abort = () => {
      request.aborted = true
      reject(options.signal.reason)
    }
    if (options.signal.aborted) abort()
    else options.signal.addEventListener("abort", abort, { once: true })
  })
}
function transport(domain, stage) {
  let submissions = 0, reads = 0
  fetchMock.mockImplementation((url, options) => {
    if (url.endsWith("/health")) return Promise.resolve(response({}))
    if (url.endsWith("/cancel")) return Promise.resolve(response({}))
    if (options.method === "POST") {
      submissions += 1
      if (stage === "submit" || submissions > 1) return hangingFetch(options)
      return Promise.resolve(response({ id: "job", job_id: "job", status: "queued" }))
    }
    reads += 1
    if (stage === "poll") return hangingFetch(options)
    if (stage === "backoff") return Promise.reject(new TypeError("offline"))
    if (domain === "discovery" && url.includes("/results")) {
      if (stage === "refine" && reads === 2) return Promise.resolve(response({ items: ["initial"] }))
      return hangingFetch(options)
    }
    if (domain === "media" && reads > 1) return hangingFetch(options)
    return Promise.resolve(response({ id: "job", job_id: "job", status: domain === "media" ? "completed" : "succeeded", result_url: "result.png" }))
  })
}

beforeEach(() => {
  vi.clearAllTimers()
  vi.mocked(fetch).mockReset()
  pending = []
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
})
afterEach(() => {
  act(() => root?.unmount())
  root = null
  document.body.replaceChildren()
  vi.clearAllTimers()
})
afterAll(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

for (const domain of ["discovery", "media"]) {
  describe(`${domain}: component through real API adapter to fetch`, () => {
    for (const action of ["unmount", "navigation", "resubmit"]) {
      it(`${action} rejects an actual native fetch with AbortError`, async () => {
        let nativeRequest
        // A data URL exercises native fetch cancellation without depending on an
        // external server. Only the destination is redirected; options are intact.
        fetchMock.mockImplementation((url, options) => {
          if (nativeRequest) return hangingFetch(options)
          nativeRequest = nativeFetch("data:application/json,%7B%7D", options)
          return nativeRequest
        })
        mount(domain === "discovery" ? useDiscoverySearch : useMediaGenerate)
        let observed
        act(() => {
          void latest.submit({ query: "old", prompt: "old" })
          observed = nativeRequest.catch(error => error)
          if (action === "unmount") { root.unmount(); root = null }
          else if (action === "navigation") navigate("/away")
          else void latest.submit({ query: "new", prompt: "new" })
        })
        expect(await observed).toMatchObject({ name: "AbortError" })
        await flush()
        if (action === "resubmit") {
          expect(latest.phase).toBe("submitting")
          expect(pending[0].signal.aborted).toBe(false)
        } else expect(vi.getTimerCount()).toBe(0)
      })
    }

    for (const stage of ["submit", "poll", "results"]) {
      for (const action of ["unmount", "navigation", "resubmit", "cancel"]) {
        it(`${action} aborts a pending ${stage} fetch, not merely its state update`, async () => {
          transport(domain, stage)
          mount(domain === "discovery" ? useDiscoverySearch : useMediaGenerate)
          await flush(() => { void latest.submit({ query: "old", prompt: "old" }) })
          if (domain === "discovery" && stage !== "submit") await advance(400)
          expect(pending).toHaveLength(1)
          const obsolete = pending[0]
          expect(obsolete.signal.aborted).toBe(false)
          if (action === "unmount") { act(() => root.unmount()); root = null }
          else if (action === "navigation") await flush(() => navigate("/away"))
          else if (action === "resubmit") await flush(() => { void latest.submit({ query: "new", prompt: "new" }) })
          else await flush(() => { void latest.cancel() })
          await flush()
          expect(obsolete.aborted).toBe(true)
          expect(obsolete.signal.aborted).toBe(true)
          if (action === "navigation") expect(node.textContent).toBe("Another page")
          if (action === "resubmit") {
            const waitingForServerCancel = domain === "discovery" && stage === "poll"
            expect(latest.phase).toBe(waitingForServerCancel ? "cancelling" : "submitting")
            expect(latest.error).toBeNull()
            expect(pending.at(-1).signal.aborted).toBe(false)
          } else {
            if (action === "cancel") {
              const serverCancelPending = domain === "discovery" && stage === "poll"
              expect(latest.phase).toBe(serverCancelPending ? "cancelling" : "idle")
            }
            if (domain !== "discovery" || stage !== "poll" || action !== "cancel") {
              expect(vi.getTimerCount()).toBe(0)
            }
          }
          const calls = fetchMock.mock.calls.length
          await advance(20000)
          expect(fetch).toHaveBeenCalledTimes(calls)
        })
      }
    }

    it("navigation stops a real adapter's HTTP retry backoff", async () => {
      transport(domain, "backoff")
      mount(domain === "discovery" ? useDiscoverySearch : useMediaGenerate)
      await flush(() => { void latest.submit({ query: "old" }) })
      if (domain === "discovery") await advance(400)
      const calls = fetchMock.mock.calls.length
      await flush(() => navigate("/away"))
      expect(vi.getTimerCount()).toBe(0)
      await advance(20000)
      const newCalls = fetchMock.mock.calls.slice(calls)
      expect(newCalls.every(([url]) => String(url).endsWith("/cancel"))).toBe(true)
    })
  })
}

it("a new discovery refinement aborts the prior same-job result fetch", async () => {
  transport("discovery", "refine")
  mount(useDiscoverySearch)
  await flush(() => { void latest.submit({ query: "old" }) })
  await advance(400)
  expect(latest.phase).toBe("ready")
  await flush(() => latest.refine({ sort: "old" }))
  const obsolete = pending[0]
  await flush(() => latest.refine({ sort: "new" }))
  expect(obsolete.aborted).toBe(true)
  expect(pending[1].signal.aborted).toBe(false)
  await flush(() => pending[1].resolve({ items: ["new"] }))
  expect(latest.results.items).toEqual(["new"])
  expect(vi.getTimerCount()).toBe(0)
})

for (const action of ["unmount", "navigation", "resubmit"]) {
  it(`${action} also aborts an in-flight media server-cancel fetch`, async () => {
    transport("media", "poll")
    const implementation = fetchMock.getMockImplementation()
    if (!implementation) throw new Error("Expected an initialized fetch mock")
    fetchMock.mockImplementation((url, options) => url.endsWith("/cancel")
      ? hangingFetch(options) : implementation(url, options))
    mount(useMediaGenerate)
    await flush(() => { void latest.submit({ prompt: "old" }) })
    await flush(() => { void latest.cancel() })
    const cancellation = pending.at(-1)
    if (action === "unmount") { act(() => root.unmount()); root = null }
    else if (action === "navigation") await flush(() => navigate("/away"))
    else await flush(() => { void latest.submit({ prompt: "new" }) })
    await flush()
    expect(cancellation.aborted).toBe(true)
    expect(cancellation.signal.aborted).toBe(true)
    if (action === "resubmit") expect(latest.phase).toBe("submitting")
    else expect(vi.getTimerCount()).toBe(0)
  })
}
