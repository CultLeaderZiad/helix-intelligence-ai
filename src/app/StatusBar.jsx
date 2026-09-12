import { Database, Clock, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { DATA_SOURCE } from "@/services"
import { API_BASE_URL } from "@/services/config"
import { formatDuration, formatInt } from "@/lib/format"
import { useTelemetry } from "./TelemetryContext"
import { useAuth } from "@/context/AuthContext"

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
  const { user, isAuthenticated } = useAuth()

  const isAdmin = user?.role === "admin" || user?.is_superuser === true || user?.is_admin === true
  const isTrial = user?.plan_id?.includes("trial") || user?.trial_days_remaining != null

  return (
    <footer className="flex h-7 shrink-0 items-center gap-4 border-t border-border bg-surface px-3 font-mono text-[10px] uppercase tracking-[0.06em] text-text-faint">
      {isAdmin ? (
        <>
          <span className="flex items-center gap-1.5">
            <Database className="h-3 w-3 text-text-faint" aria-hidden="true" />
            <span className={DATA_SOURCE === "mock" ? "text-warning" : "text-success font-medium"}>
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
        </>
      ) : (
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
          <span className="text-text-muted font-medium tracking-wider">ALL SYSTEMS NOMINAL</span>
        </span>
      )}

      <span className="ml-auto flex items-center gap-4">
        {isAuthenticated && isTrial && (
          <span className="flex items-center gap-1.5 border-l border-border pl-4">
            <span className="text-accent">{user.trial_days_remaining}d left</span>
            <span className="text-text-muted">·</span>
            <span className="text-accent">{Number(user.credit_balance || 0).toFixed(1)}cr</span>
            {user.daily_credit_limit != null && (
              <>
                <span className="text-text-muted">·</span>
                <span className="flex items-center gap-1">
                  <span className="text-text-muted">today</span>
                  <span
                    className={cn("tnum", {
                      "text-success": Number(user.daily_credits_remaining || 0) > 1,
                      "text-warning": Number(user.daily_credits_remaining || 0) > 0 && Number(user.daily_credits_remaining || 0) <= 1,
                      "text-danger": Number(user.daily_credits_remaining || 0) <= 0,
                    })}
                  >
                    {Number(user.daily_credits_used || 0).toFixed(1)}/{Number(user.daily_credit_limit || 0).toFixed(1)}
                  </span>
                </span>
              </>
            )}
          </span>
        )}

        <span className="flex items-center gap-1.5">
          {isAdmin && telemetry.lastJobId ? (
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

        <span className="hidden items-center gap-2 border-l border-border pl-3 sm:flex">
          <img
            src="/brand/helix-logo.png"
            alt="Helix"
            className="h-3.5 w-3.5 rounded-[2px] object-contain opacity-80"
          />
          <span className="font-mono text-[9px] tracking-[0.12em] text-text-faint">
            POWERED BY HELIX
          </span>
        </span>
      </span>
    </footer>
  )
}
