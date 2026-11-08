import { describe, expect, it } from "vitest"
import { JOB_STATUS, JOB_TERMINAL_STATUSES, isJobCancelled, isJobTerminal } from "@/lib/constants"

// Must match SCRAPE_JOB in backend/app/core/state_machines.py.
const SERVER_TERMINAL = ["succeeded", "failed", "cancelled", "timed_out"]
const SERVER_ACTIVE = ["queued", "running"]

describe("discover job status constants", () => {
  it("mirror the server values", () => {
    expect(Object.values(JOB_STATUS).sort()).toEqual([...SERVER_ACTIVE, ...SERVER_TERMINAL].sort())
  })
  it("treat every server terminal status, and the legacy alias, as terminal", () => {
    for (const s of SERVER_TERMINAL) expect(isJobTerminal(s)).toBe(true)
    expect(isJobTerminal("canceled")).toBe(true)
    expect(JOB_TERMINAL_STATUSES).toHaveLength(5)
  })
  it("treat active and unknown statuses as non-terminal", () => {
    for (const s of [...SERVER_ACTIVE, "cancelling", "", undefined, null]) expect(isJobTerminal(s)).toBe(false)
  })
  it("accept both cancel spellings", () => {
    expect(isJobCancelled("cancelled")).toBe(true)
    expect(isJobCancelled("canceled")).toBe(true)
    expect(isJobCancelled("failed")).toBe(false)
  })
})
