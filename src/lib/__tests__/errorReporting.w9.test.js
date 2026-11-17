import { describe, expect, it, vi } from "vitest"
import { beforeSend, initErrorReporting, scrub } from "../errorReporting"

vi.mock("@sentry/react", () => ({ init: vi.fn() }))

describe("W9 optional Sentry (frontend)", () => {
  it("stays off without VITE_SENTRY_DSN", async () => {
    const Sentry = await import("@sentry/react")
    expect(await initErrorReporting({})).toBe(false)
    expect(await initErrorReporting({ VITE_SENTRY_DSN: "  " })).toBe(false)
    expect(Sentry.init).not.toHaveBeenCalled()
  })

  it("starts collecting no PII and no tracing when a DSN is set", async () => {
    /** @type {any} */
    const Sentry = await import("@sentry/react")
    expect(await initErrorReporting({ VITE_SENTRY_DSN: "https://k@o0.ingest.sentry.io/1", MODE: "production" })).toBe(true)
    const opts = Sentry.init.mock.calls[0][0]
    expect(opts.dataCollection).toEqual({ userInfo: false, cookies: false, httpHeaders: false, httpBodies: [] })
    expect(opts.tracesSampleRate).toBe(0)
  })

  it("scrubs auth headers, cookies, bodies and emails", () => {
    const out = beforeSend({
      message: "failed for someone@example.com",
      user: { id: "u1", email: "someone@example.com", ip_address: "1.2.3.4" },
      request: {
        url: "https://api/x",
        headers: { Authorization: "Bearer abc", Cookie: "s=1", Accept: "application/json" },
        cookies: { s: "1" },
        data: { password: "x" },
      },
    })
    expect(out.message).toBe("failed for [email]")
    expect(out.user).toEqual({ id: "u1" })
    expect(out.request.headers.Authorization).toBe("[Filtered]")
    expect(out.request.headers.Cookie).toBe("[Filtered]")
    expect(out.request.headers.Accept).toBe("application/json")
    expect(out.request.cookies).toBeUndefined()
    expect(out.request.data).toBeUndefined()
    expect(scrub({ access_token: "t" })).toEqual({ access_token: "[Filtered]" })
  })
})
