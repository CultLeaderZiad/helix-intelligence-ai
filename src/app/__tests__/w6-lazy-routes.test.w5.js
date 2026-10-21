/// <reference types="node" />
import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const appSource = readFileSync("src/App.jsx", "utf8")

describe("W6 route-level lazy loading", () => {
  it("defers the public landing page and admin shell", () => {
    expect(appSource).toContain('const LandingPage = safeLazy(() => import("@/pages/LandingPage")')
    expect(appSource).toContain('const AdminShell = safeLazy(() => import("@/app/admin/AdminShell")')
    expect(appSource).not.toMatch(/^import\s+\{[^}]*\b(?:LandingPage|AdminShell)\b[^}]*\}\s+from/m)
  })

  it("keeps Discover, its authenticated shell, and route protection intact", () => {
    expect(appSource).toContain('const DiscoverPage = safeLazy(() => import("@/pages/DiscoverPage")')
    expect(appSource).toContain('import { AppShell } from "@/app/AppShell"')
    expect(appSource).toContain('import { ProtectedRoute } from "@/app/ProtectedRoute"')
    expect(appSource).toContain('<Route path="/discover" element={<DiscoverPage />} />')
    expect(appSource).toContain('<Suspense fallback={<PageLoader />}>')
  })
})
