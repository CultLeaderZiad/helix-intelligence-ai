import { afterEach, describe, expect, it, vi } from "vitest"

afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })

describe("W5 product boundaries", () => {
  it("shows only Discover by default and hides billing administration", async () => {
    vi.stubEnv("VITE_ENABLE_EXPERIMENTAL_FEATURES", "false")
    vi.resetModules()
    const { NAV_SECTIONS } = await import("../navigation")
    const { ADMIN_NAV_GROUPS } = await import("../admin/adminNavigation")
    expect(NAV_SECTIONS.map((section) => section.path)).toEqual(["/discover"])
    const paths = ADMIN_NAV_GROUPS.flatMap((group) => group.items.map((item) => item.path))
    expect(paths).not.toContain("/admin/subscriptions")
    expect(paths).not.toContain("/admin/usage")
    expect(paths).toContain("/admin/access-requests")
  })

  it("requires an explicit opt-in for experimental navigation", async () => {
    vi.stubEnv("VITE_ENABLE_EXPERIMENTAL_FEATURES", "true")
    vi.resetModules()
    const { NAV_SECTIONS } = await import("../navigation")
    expect(NAV_SECTIONS.map((section) => section.path)).toContain("/create")
  })
})
