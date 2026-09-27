import React from "react"
import { Pause, Play, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * JobProgress — terminal transcript driven entirely by the real job envelope
 * (job.logs / job.stage_index / counters). No CSS theater: if the worker
 * hasn't written a line, nothing is shown.
 */
function LogLine({ line }) {
  const danger = /(failed|error|blocked|rate_limited|exhausted|unavailable|401|403|429)/i.test(line)
  const warn = /(rejected|pause|throttle|skipped)/i.test(line)
  const ok = /( · ok|· ok$|=ok|succeeded|ready|icp_ok)/i.test(line)
  const tone = danger ? "text-danger" : warn ? "text-warning" : ok ? "text-success" : "text-text-muted"
  return <div className={cn("truncate", tone)}>{line}</div>
}

export function JobProgress({ job, leadsCount, onPause, onResume, onRefresh }) {
  if (!job) return null

  const running = job.status === "running" || job.status === "queued"
  const paused = job.status === "paused"
  const done = job.status === "succeeded"
  const failed = job.status === "failed"
  const elapsed = job.elapsed_ms ? (job.elapsed_ms / 1000).toFixed(1) : "0.0"
  const count = leadsCount !== undefined && leadsCount !== null ? leadsCount : job.leads_count || 0
  const logs = (job.logs || []).slice(-9)

  return (
    <div className="rounded-[4px] border border-border bg-surface p-3.5 sm:p-4 font-mono">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn(
                "h-2 w-2 rounded-full shrink-0",
                running && "bg-accent animate-pulse",
                paused && "bg-warning",
                done && "bg-success",
                failed && "bg-danger"
              )}
            />
            <span className={cn("font-semibold", running ? "text-accent" : paused ? "text-warning" : done ? "text-success" : "text-danger")}>
              {job.status}
            </span>
            <span className="text-text-muted">{job.job_id?.slice(0, 8)}</span>
            <span className="text-text-faint">·</span>
            <span className="text-text-muted">
              stage {Math.min((job.stage_index ?? 0) + 1, job.stages_total || 9)}/{job.stages_total || 9} {job.stage}
            </span>
            <span className="text-text-faint">·</span>
            <span className="text-text-faint">
              {job.engine_default} · {job.mode}
              {job.recipe_id ? ` · ${job.recipe_id}` : ""}
            </span>
            {job.robots_obey === false && (
              <span className="rounded border border-warning/50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-warning">
                robots off
              </span>
            )}
          </div>

          <div className="space-y-1 pt-1 text-[11px] leading-relaxed">
            {logs.length > 0 ? (
              logs.map((line, i) => <LogLine key={i} line={line} />)
            ) : (
              <div className="text-text-faint">waiting for worker output…</div>
            )}
          </div>

          {job.error_msg && (
            <div className="pt-1 text-[11px] text-danger">{job.error_msg}</div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0 pl-4 border-l border-border/60">
          <div className="text-right">
            <span className="tnum text-2xl sm:text-3xl font-bold text-white leading-none">{count}</span>
            <div className="text-[10.5px] text-text-faint mt-1">
              leads · {job.pages_fetched || 0} pages · {job.pages_blocked || 0} blocked · {elapsed}s
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {running && onPause && (
              <button
                type="button"
                onClick={onPause}
                className="flex items-center gap-1 rounded border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:border-warning/50"
              >
                <Pause className="h-3 w-3" /> pause
              </button>
            )}
            {paused && onResume && (
              <button
                type="button"
                onClick={onResume}
                className="flex items-center gap-1 rounded border border-accent bg-accent/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent"
              >
                <Play className="h-3 w-3" /> resume
              </button>
            )}
            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                className="flex items-center gap-1 rounded border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted hover:text-white"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default JobProgress
