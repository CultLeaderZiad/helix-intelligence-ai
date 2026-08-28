import { useCallback } from "react"
import { adminService } from "@/services"
import { useAsync } from "./useAsync"

/**
 * ============================================================
 * ADMIN OVERVIEW
 * ============================================================
 * The single route the admin Overview page uses to reach data — the same
 * page → hook → service contract Discover follows. Components on the page
 * never import `adminService` directly; they read what this hook returns.
 *
 * The three panels load as one unit on purpose: a half-populated
 * operations dashboard (stats in, health still spinning) reads as a
 * system fault rather than a loading state. One loading flag, one error,
 * one retry for the whole surface.
 * ============================================================
 */
export function useAdminOverview() {
  const fetcher = useCallback(
    () =>
      Promise.all([
        adminService.getOverviewStats(),
        adminService.listRecentJobs(),
        adminService.getSystemHealth(),
        adminService.listOrganizations(),
        adminService.listUsers(),
      ]),
    [],
  )

  const { data, error, loading, refetch } = useAsync(fetcher, [fetcher])

  const [stats, jobs, health, organizations, users] = data ?? [null, null, null, null, null]

  return {
    stats,
    jobs: jobs?.items ?? [],
    health,
    organizations: organizations ?? [],
    users: users ?? [],
    loading,
    error,
    refetch,
  }
}
