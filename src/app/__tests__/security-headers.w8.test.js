import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const vercel = JSON.parse(readFileSync("vercel.json", "utf8"))
const all = vercel.headers.find((rule) => rule.source === "/(.*)")
const header = (name) => all?.headers.find((h) => h.key.toLowerCase() === name.toLowerCase())?.value
const directives = Object.fromEntries(
  (header("Content-Security-Policy") || "")
    .split(";")
    .map((part) => part.trim().split(/\s+/))
    .filter((parts) => parts[0])
    .map(([name, ...values]) => [name, values]),
)

describe("W8 frontend security headers (vercel.json)", () => {
  it("sends a CSP on every path that blocks framing and inline or remote script", () => {
    expect(all).toBeTruthy()
    expect(directives["frame-ancestors"]).toEqual(["'none'"])
    expect(directives["object-src"]).toEqual(["'none'"])
    expect(directives["base-uri"]).toEqual(["'self'"])
    expect(directives["script-src"]).toContain("'self'")
    expect(directives["script-src"]).not.toContain("'unsafe-inline'")
    expect(directives["script-src"]).not.toContain("'unsafe-eval'")
    expect(directives["script-src"].filter((s) => s.startsWith("https:") && s !== "https://plausible.io")).toEqual([])
  })

  it("lets the browser reach the production API it is built for, and nothing else by script", () => {
    const env = readFileSync(".env.production", "utf8")
    const apiOrigin = new URL(env.match(/^VITE_API_BASE_URL=(.+)$/m)[1].trim()).origin
    expect(directives["connect-src"]).toContain(apiOrigin)
    expect(directives["connect-src"]).not.toContain("*")
    expect(directives["connect-src"]).not.toContain("https:")
  })

  it("adds the other hardening headers", () => {
    expect(header("X-Frame-Options")).toBe("DENY")
    expect(header("X-Content-Type-Options")).toBe("nosniff")
    expect(header("Referrer-Policy")).toBe("strict-origin-when-cross-origin")
    expect(header("Permissions-Policy")).toMatch(/camera=\(\)/)
  })

  it("index.html carries no inline executable script the CSP would block", () => {
    const html = readFileSync("index.html", "utf8")
    const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)([^>]*)>/g)].map((m) => m[1])
    expect(inline.every((attrs) => /type="application\/ld\+json"/.test(attrs))).toBe(true)
  })
})
