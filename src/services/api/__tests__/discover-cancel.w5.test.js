import { afterEach, describe, expect, it, vi } from "vitest"

const { request } = vi.hoisted(() => ({ request: vi.fn() }))
vi.mock("../http", () => ({ request }))

import discoverService from "../discoverService.api"

afterEach(() => vi.resetAllMocks())

describe("Discover cancellation API", () => {
  it("posts to the tenant-authorized job cancellation route without a search signal", async () => {
    request.mockResolvedValue({ job_id: "job/1", status: "cancelled" })

    await discoverService.cancelJob("job/1")

    expect(request).toHaveBeenCalledWith("/discovery/jobs/job%2F1/cancel", {
      method: "POST",
    })
  })
})
