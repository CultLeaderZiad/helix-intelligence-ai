import { describe, expect, it } from "vitest"
import { normalizeFrontendEnvironment, resolveApiBaseUrl } from "../origin.js"

describe("API origin configuration", () => {
  it("defaults to same-origin routing and accepts loopback development URLs", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("/api")
    expect(resolveApiBaseUrl("/api/", "preview", true)).toBe("/api")
    expect(resolveApiBaseUrl("http://127.0.0.1:8000/api", "development")).toBe(
      "http://127.0.0.1:8000/api"
    )
    expect(resolveApiBaseUrl("http://[::1]:8000/api", "test")).toBe(
      "http://[::1]:8000/api"
    )
  })

  it("rejects remote API origins outside production, including production-mode previews", () => {
    for (const environment of ["development", "test", "staging", "preview"]) {
      expect(() => resolveApiBaseUrl("https://api.example.invalid", environment, true)).toThrow()
    }
  })

  it("allows only public HTTPS origins in an explicitly production build", () => {
    expect(
      resolveApiBaseUrl("https://api.example.invalid/v1", "production", true)
    ).toBe("https://api.example.invalid/v1")
    expect(() => resolveApiBaseUrl("https://api.example.invalid", "production")).toThrow()
    expect(() => resolveApiBaseUrl("http://api.example.invalid", "production", true)).toThrow()
    expect(() => resolveApiBaseUrl("http://localhost:8000", "production", true)).toThrow()
  })

  it("rejects ambiguous paths, credentials, and unknown environment values", () => {
    for (const value of ["//api.example.invalid", "api", "/api?token=x", "http://user:pass@localhost:8000"]) {
      expect(() => resolveApiBaseUrl(value)).toThrow()
    }
    expect(() => normalizeFrontendEnvironment("unknown")).toThrow()
  })
})
