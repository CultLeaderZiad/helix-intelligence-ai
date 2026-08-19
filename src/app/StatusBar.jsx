import { Database, Clock, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { DATA_SOURCE } from "@/services"
import { API_BASE_URL } from "@/services/config"
import { formatDuration, formatInt } from "@/lib/format"
import { useTelemetry } from "./TelemetryContext"

/**
 * State word tone. The live *dot* carries the accent (it is a status
 * indicator); the word beside it does not, so lime stays a single signal
 * in the strip rather than two.
 */
const STATE_TONE = {
  idle: "text-text-faint",
  running: "text-text",
  ready: "text-success",
  error: "text-danger",
}

/**
 * Bottom instrument strip. Every value here is measured, not invented:
 * source comes from config, latency from the service response, records
 * from the completed job.
 */
export function StatusBar() {
  const { telemetry } = useTelemetry()

  return (
    <footer className="flex h-7 shrink-0 items-center gap-4 border-t border-border bg-surface px-3 font-mono text-[10px] uppercase tracking-[0.06em] text-text-faint">
      <span className="flex items-center gap-1.5">
        <Database className="h-3 w-3" aria-hidden="true" />
        <span className={DATA_SOURCE === "mock" ? "text-warning" : "text-success"}>
          {DATA_SOURCE === "mock" ? "mock fixtures" : API_BASE_URL}
        </span>
      </span>

      <span className="h-3 w-px bg-border" aria-hidden="true" />

      <span className="flex items-center gap-1.5">
        <Layers className="h-3 w-3" aria-hidden="true" />
        <span className="tnum">
          {telemetry.records === null ? "no set" : `${formatInt(telemetry.records)} rec`}
        </span>
      </span>

      <span className="flex items-center gap-1.5">
        <Clock className="h-3 w-3" aria-hidden="true" />
        <span className="tnum">
          {telemetry.tookMs === null ? "—" : formatDuration(telemetry.tookMs)}
        </span>
      </span>

      <span className="tnum hidden sm:inline">req {formatInt(telemetry.requests)}</span>

      <span className="ml-auto flex items-center gap-1.5">
        {telemetry.lastJobId ? (
          <span className="hidden truncate text-text-muted md:inline">
            {telemetry.lastJobId}
          </span>
        ) : null}
        <span
          className={cn("h-1.5 w-1.5 rounded-full", {
            "bg-border-strong": telemetry.state === "idle",
            "bg-accent animate-pulse": telemetry.state === "running",
            "bg-success": telemetry.state === "ready",
            "bg-danger": telemetry.state === "error",
          })}
          aria-hidden="true"
        />
        <span className={cn(STATE_TONE[telemetry.state])}>{telemetry.state}</span>
      </span>
    </footer>
  )
}
