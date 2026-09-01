import { Database, Clock, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { DATA_SOURCE } from "@/services"
import { API_BASE_URL } from "@/services/config"
import { formatDuration, formatInt } from "@/lib/format"
import { useTelemetry } from "./TelemetryContext"
import { useAuth } from "@/context/AuthContext"

function GithubIcon({ className = "h-3 w-3", ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} {...props}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  )
}

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

  const isTrial = user?.plan_id?.includes("trial") || user?.trial_days_remaining != null

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

        <span className="hidden items-center gap-2 border-l border-border pl-3 sm:flex">
          <img
            src="/brand/helix-logo.png"
            alt="Helix"
            className="h-3.5 w-3.5 rounded-[2px] object-contain opacity-80"
          />
          <span className="font-mono text-[9px] tracking-[0.12em] text-text-faint">
            POWERED BY HELIX
          </span>
          <span className="text-border-strong">·</span>
          <a
            href="https://github.com/CultLeaderZiad/helix-intelligence-ai"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Helix on GitHub"
            className="text-text-faint hover:text-text transition-colors flex items-center gap-1"
          >
            <GithubIcon className="h-3 w-3" />
            <span className="hidden lg:inline text-[9px]">GITHUB</span>
          </a>
        </span>
      </span>
    </footer>
  )
}
