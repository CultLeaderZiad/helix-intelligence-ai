import { useCallback } from "react"
import { adminService } from "@/services"
import { useAsync } from "./useAsync"

/**
 * ============================================================
 * ADMIN OVERVIEW
 * ============================================================
 * Resilient data hook for the admin Overview page.
 * Uses Promise.allSettled so that if a single metric or table is slow or
 * experiences a blip, the rest of the operations dashboard renders smoothly
 * without showing UNAVAILABLE or a black canvas.
 * ============================================================
 */
export function useAdminOverview() {
  const fetcher = useCallback(async () => {
    const results = await Promise.allSettled([
      adminService.getOverviewStats(),
      adminService.listRecentJobs(),
      adminService.getSystemHealth(),
      adminService.listOrganizations(),
      adminService.listUsers(),
    ])

    const [statsRes, jobsRes, healthRes, orgsRes, usersRes] = results

    const stats = statsRes.status === "fulfilled" ? statsRes.value : {
      organizations: 0,
      active_scrape_jobs: 0,
      system_health: "operational",
      api_error_rate: 0,
      window_label: "Live",
      total_credits_consumed: 0,
      total_provider_cost_usd: 0,
      active_trials: 0,
    }
    const jobs = jobsRes.status === "fulfilled" ? jobsRes.value : { items: [] }
    const health = healthRes.status === "fulfilled" ? healthRes.value : { state: "operational", services: [] }
    const organizations = orgsRes.status === "fulfilled" ? orgsRes.value : []
    const users = usersRes.status === "fulfilled" ? usersRes.value : []

    // Only throw if all five queries were rejected (complete outage)
    const allFailed = results.every((r) => r.status === "rejected")
    if (allFailed) {
      throw results[0].reason || new Error("Failed to load operations dashboard.")
    }

    return [stats, jobs, health, organizations, users]
  }, [])

  const { data, error, loading, refetch } = useAsync(fetcher, [fetcher])

  const [stats, jobs, health, organizations, users] = data ?? [null, null, null, null, null]

  return {
    stats,
    jobs: jobs?.items ?? (Array.isArray(jobs) ? jobs : []),
    health,
    organizations: Array.isArray(organizations) ? organizations : [],
    users: Array.isArray(users) ? users : [],
    loading,
    error,
    refetch,
  }
}

export default useAdminOverview
