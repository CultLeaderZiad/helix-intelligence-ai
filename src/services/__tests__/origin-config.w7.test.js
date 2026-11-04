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

  it("rejects IP literals and numeric host aliases in production", () => {
    for (const host of ["10.0.0.1", "192.168.1.1", "169.254.169.254", "100.64.0.1", "[fc00::1]", "[fe80::1]", "[::ffff:10.0.0.1]", "2130706433", "127.1", "0x7f000001", "8.8.8.8"]) {
      expect(() => resolveApiBaseUrl(`https://${host}`, "production", true)).toThrow()
    }
  })

  it("uses production rules for an unclassified production-mode build", () => {
    expect(resolveApiBaseUrl(undefined, undefined, true)).toBe("/api")
    expect(() => resolveApiBaseUrl("http://localhost:8000", undefined, true)).toThrow()
    expect(resolveApiBaseUrl("http://localhost:8000", "preview", true)).toBe("http://localhost:8000")
  })
})
