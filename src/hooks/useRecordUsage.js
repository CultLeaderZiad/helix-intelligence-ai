import { useCallback, useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { accountService } from "@/services"

/** This month's Metapi records for the workspace (GET /account/record-usage). */
export function useRecordUsage() {
  const { user } = useAuth()
  const [usage, setUsage] = useState(null)
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)
  const scope = `${user?.id ?? ""}:${user?.organization_id ?? ""}`

  useEffect(() => {
    let active = true
    setError(false)
    accountService.getRecordUsage()
      .then((next) => { if (active) setUsage(next) })
      .catch(() => { if (active) { setUsage(null); setError(true) } })
    return () => { active = false }
  }, [scope, version])

  const refresh = useCallback(() => setVersion((v) => v + 1), [])
  return { usage, error, refresh }
}
