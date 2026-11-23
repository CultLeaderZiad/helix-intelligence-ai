import { useCallback, useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { accountService } from "@/services"

/**
 * This month's Metapi records for the workspace, read from the existing
 * GET /account/usage/today (workspace_daily_usage.records; no second counter).
 */
export function toRecordUsage(raw) {
  if (!raw || typeof raw.records_used_this_month !== "number") return null
  return {
    used: raw.records_used_this_month,
    cap: raw.records_cap_this_month,
    remaining: raw.records_remaining_this_month,
    warning: Boolean(raw.records_warning),
    platformPaused: Boolean(raw.platform_records_paused),
    estimates: raw.records_estimates || null,
  }
}

export function useRecordUsage() {
  const { user } = useAuth()
  const [loaded, setLoaded] = useState({ scope: null, usage: null })
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)
  const scope = `${user?.id ?? ""}:${user?.organization_id ?? ""}`

  useEffect(() => {
    let active = true
    setError(false)
    accountService.getTodayUsage()
      .then((next) => { if (active) setLoaded({ scope, usage: toRecordUsage(next) }) })
      .catch(() => { if (active) { setLoaded({ scope, usage: null }); setError(true) } })
    return () => { active = false }
  }, [scope, version])

  const refresh = useCallback(() => setVersion((v) => v + 1), [])
  // Never show another workspace's numbers while this one's are loading.
  const usage = loaded.scope === scope ? loaded.usage : null
  return { usage, error, refresh }
}
