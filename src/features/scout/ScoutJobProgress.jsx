import React from "react"
import { cn } from "@/lib/utils"

export function ScoutJobProgress({ job, leadsCount }) {
  if (!job) return null

  const isRunning = job.status === "running" || job.status === "queued"
  const isComplete = job.status === "succeeded"
  const isFailed = job.status === "failed"

  const elapsedSec = job.elapsed_ms ? (job.elapsed_ms / 1000).toFixed(1) : "0.0"
  const count = leadsCount !== undefined ? leadsCount : (job.leads_count || 0)

  return (
    <div className="rounded-[4px] border border-border bg-surface p-3.5 sm:p-4 font-mono">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        {/* Left: Terminal Transcript */}
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs">
            <span
              className={cn(
                "h-2 w-2 rounded-full shrink-0",
                isRunning && "bg-accent animate-pulse",
                isComplete && "bg-success",
                isFailed && "bg-danger"
              )}
              style={isRunning ? { boxShadow: "0 0 6px rgba(215, 255, 79, 0.7)" } : undefined}
            />
            <span className={cn("font-semibold", isRunning ? "text-accent" : isComplete ? "text-success" : "text-danger")}>
              {isRunning ? "running" : isComplete ? "completed" : "failed"}
            </span>
            <span className="text-text-muted">{job.job_id}</span>
            <span className="text-text-faint">·</span>
            <span className="text-text-muted">
              stage {job.stage_index || 1}/{job.stages_total || 4} {job.stage}
            </span>
          </div>

          {/* Logs lines */}
          <div className="space-y-1 pt-1 text-[11px] leading-relaxed text-text-muted font-mono">
            {(job.logs && job.logs.length > 0 ? job.logs.slice(-4) : ["> worker started"]).map((log, idx) => {
              const isVerified = log.includes("verified")
              const isOk = log.includes("ok")
              return (
                <div key={idx} className="truncate">
                  {log.split(" · ").map((part, pIdx) => {
                    if (pIdx === 0) {
                      return <span key={pIdx} className="text-text">{part}</span>
                    }
                    if (part.includes("verified")) {
                      return (
                        <span key={pIdx}>
                          {" · "}
                          <span className="text-success font-medium">{part}</span>
                        </span>
                      )
                    }
                    if (part.includes("ok")) {
                      return (
                        <span key={pIdx}>
                          {" · "}
                          <span className="text-success font-medium">ok</span>
                        </span>
                      )
                    }
                    return <span key={pIdx}> · {part}</span>
                  })}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right: Big Counter Readout */}
        <div className="flex flex-col items-end shrink-0 pl-4 border-l border-border/60">
          <span className="tnum text-2xl sm:text-3xl font-bold font-mono text-white leading-none">
            {count}
          </span>
          <span className="text-[10.5px] font-mono text-text-faint mt-1">
            leads · {elapsedSec}s
          </span>
        </div>
      </div>
    </div>
  )
}
