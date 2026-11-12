import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { classifyAuthFailure } from "@/features/auth/authFailure"
import { en, ar } from "@/i18n/w8Product"
import { RecordsMeter } from "../BillingPage"
import { ServiceError } from "@/services/http"

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe("W9 rate limits in the UI", () => {
  it("tells a request limit apart from the sign-in lock", () => {
    expect(classifyAuthFailure({ status: 429, code: "rate_limited" })).toBe("rate_limited")
    expect(classifyAuthFailure({ status: 429, code: "too_many_sign_in_attempts" })).toBe("locked")
    expect(classifyAuthFailure({ status: 401 })).toBe("credentials")
  })

  it("keeps Retry-After on the error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: { code: "rate_limited", message: "Too many requests." } }),
      { status: 429, headers: { "Content-Type": "application/json", "Retry-After": "42" } },
    )))
    const { request } = await import("@/services/http")
    const err = await request("/discovery/jobs", { method: "POST", body: {} }).catch((e) => e)
    expect(err).toBeInstanceOf(ServiceError)
    expect(err.status).toBe(429)
    expect(err.code).toBe("rate_limited")
    expect(err.retryAfter).toBe(42)
  })

  it("has the limit message in English and Arabic", () => {
    expect(en.rateLimited(30)).toMatch(/30 seconds/)
    expect(ar.rateLimited(30)).toMatch(/30/)
    expect(ar.recordsMeterFull).not.toBe(en.recordsMeterFull)
  })
})

describe("W9 records meter", () => {
  it("shows stored counts and nothing when the server sent none", () => {
    const { container } = render(<RecordsMeter usage={null} w8={en} />)
    expect(container.textContent).toBe("")
    render(<RecordsMeter usage={{ records_used_this_month: 45, records_cap_this_month: 150 }} w8={en} />)
    expect(screen.getByText(/45 of 150 ad records used/)).toBeTruthy()
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("45")
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("warns when the workspace or the platform is out of records", () => {
    render(<RecordsMeter usage={{ records_used_this_month: 150, records_cap_this_month: 150 }} w8={en} />)
    expect(screen.getByRole("alert").textContent).toBe(en.recordsMeterFull)
    cleanup()
    render(<RecordsMeter usage={{ records_used_this_month: 10, records_cap_this_month: 150, platform_records_paused: true }} w8={ar} />)
    expect(screen.getByRole("alert").textContent).toBe(ar.recordsPlatformPaused)
  })
})
