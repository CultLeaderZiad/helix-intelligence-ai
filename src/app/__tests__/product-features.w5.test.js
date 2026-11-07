import { afterEach, describe, expect, it, vi } from "vitest"

afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })

describe("W5 product boundaries", () => {
  it("shows only Discover by default and hides billing administration", async () => {
    vi.stubEnv("VITE_ENABLE_EXPERIMENTAL_FEATURES", "false")
    vi.resetModules()
    const { visibleSections } = await import("../navigation")
    const { ADMIN_NAV_GROUPS } = await import("../admin/adminNavigation")
    expect(visibleSections({}).map((section) => section.path)).toEqual(["/discover"])
    const paths = ADMIN_NAV_GROUPS.flatMap((group) => group.items.map((item) => item.path))
    expect(paths).not.toContain("/admin/subscriptions")
    expect(paths).not.toContain("/admin/usage")
    expect(paths).not.toContain("/admin/health")
    expect(paths).toContain("/admin/access-requests")
  })

  it("W8: Monitors and Boards follow workspace flags, not the experimental build switch", async () => {
    vi.stubEnv("VITE_ENABLE_EXPERIMENTAL_FEATURES", "true")
    vi.resetModules()
    const { visibleSections } = await import("../navigation")
    expect(visibleSections({}).map((section) => section.path)).toEqual(["/discover"])
    expect(visibleSections({ monitors: true }).map((section) => section.path)).toEqual(["/discover", "/monitors"])
    expect(visibleSections({ monitors: true, swipe_files: true, team_accounts: true }).map((section) => section.path))
      .toEqual(["/discover", "/monitors", "/swipe-files"])
  })
})
