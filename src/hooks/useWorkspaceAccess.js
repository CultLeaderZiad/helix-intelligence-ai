import { useCallback, useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { accountService } from "@/services"

export function useWorkspaceAccess() {
  const { user } = useAuth()
  const [access, setAccess] = useState(null)
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const scope = `${user?.id ?? ""}:${user?.organization_id ?? ""}`

  useEffect(() => {
    let active = true
    setAccess(null)
    setUsage(null)
    setLoading(true)
    setError(false)
    Promise.all([accountService.getAccess(), accountService.getTodayUsage()])
      .then(([nextAccess, nextUsage]) => {
        if (active) { setAccess(nextAccess); setUsage(nextUsage) }
      })
      .catch(() => { if (active) setError(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [scope, version])

  const refresh = useCallback(() => setVersion((current) => current + 1), [])
  const requestAccess = useCallback(async (note) => {
    setSubmitting(true)
    try {
      await accountService.createAccessRequest(["discover"], note, access?.org_id)
      refresh()
    } finally { setSubmitting(false) }
  }, [access?.org_id, refresh])

  return { access, usage, loading, error, submitting, refresh, requestAccess }
}
