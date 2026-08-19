import { createContext, useContext, useMemo, useState, useCallback } from "react"

/**
 * Shell-level telemetry. The status bar must report what the client
 * actually did — request count, last latency, active source — rather
 * than decorative filler. Features publish into it; the shell renders it.
 */
const TelemetryContext = createContext(null)

const INITIAL = {
  lastJobId: null,
  lastQuery: null,
  records: null,
  tookMs: null,
  requests: 0,
  state: "idle",
}

export function TelemetryProvider({ children }) {
  const [telemetry, setTelemetry] = useState(INITIAL)

  const report = useCallback((patch) => {
    setTelemetry((prev) => ({
      ...prev,
      ...patch,
      requests: patch.countRequest ? prev.requests + 1 : prev.requests,
    }))
  }, [])

  const value = useMemo(() => ({ telemetry, report }), [telemetry, report])

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext)
  if (!ctx) throw new Error("useTelemetry must be used inside TelemetryProvider")
  return ctx
}
