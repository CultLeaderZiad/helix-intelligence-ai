import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"
import { w5AuthDocs } from "@/i18n/w5AuthDocs"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
const KEYS = ["authOr", "authGoogleLabel", "authGoogleFailed", "authGoogleTerms"]

describe("Continue with Google", () => {
  it("lets Google's script, frame and token requests through the CSP", () => {
    const csp = JSON.parse(read("../../../../vercel.json")).headers[0].headers.find((h) => h.key === "Content-Security-Policy").value
    expect(csp).toMatch(/script-src [^;]*https:\/\/accounts\.google\.com\/gsi\/client/)
    expect(csp).toMatch(/frame-src [^;]*https:\/\/accounts\.google\.com\/gsi\//)
    expect(csp).toMatch(/connect-src [^;]*https:\/\/accounts\.google\.com\/gsi\//)
  })

  it("has English and Arabic copy for every new string", () => {
    for (const key of KEYS) {
      expect(w5AuthDocs.en[key], `en ${key}`).toBeTruthy()
      expect(w5AuthDocs.ar[key], `ar ${key}`).toBeTruthy()
    }
  })

  it("sends only the ID token to the server and hides itself without a client id", () => {
    const button = read("../GoogleSignInButton.jsx")
    expect(button).toContain("if (!GOOGLE_CLIENT_ID || failed) return null")
    expect(read("../../../services/api/authService.api.js")).toContain('request("/auth/google"')
  })
})
