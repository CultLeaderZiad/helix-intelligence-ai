import { ProgressBar } from "@/components/ui/ProgressBar"
import { Button } from "@/components/ui/Button"
import { formatDuration, formatInt } from "@/lib/format"
import { cn } from "@/lib/utils"

/**
 * Live job readout.
 *
 * Everything rendered here is a value the service reported: stage label,
 * stage index, fractional progress, records discovered so far, elapsed
 * time. There is no indeterminate spinner standing in for real state —
 * if the poll stops, this display stops with it.
 */
export function JobProgress({ job, onCancel }) {
  if (!job) return null

  const failed = job.status === "failed"

  return (
    <div className="flex shrink-0 flex-col gap-2 border-b border-border bg-surface px-3 py-2.5">
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "h-1.5 w-1.5 shrink-0 rounded-full",
            failed ? "bg-danger" : "bg-accent animate-pulse",
          )}
          aria-hidden="true"
        />
        <span className="text-[13px] text-text">
          {failed ? "Discovery failed" : job.stage_label}
        </span>

        <span className="label-mono">
          stage {Math.min(job.stage_index + 1, job.stages_total)}/{job.stages_total}
        </span>

        <span className="ml-auto flex items-center gap-3">
          <span className="tnum font-mono text-[11px] text-text-muted">
            {formatInt(job.records_found)} found
          </span>
          <span className="tnum font-mono text-[11px] text-text-faint">
            {formatDuration(job.elapsed_ms)}
          </span>
          {!failed && onCancel ? (
            <Button size="xs" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          ) : null}
        </span>
      </div>

      <ProgressBar value={job.progress} tone={failed ? "danger" : "accent"} striped={!failed} />

      <div className="flex items-center gap-2">
        <span className="tnum font-mono text-[10px] text-text-faint">
          {Math.round(job.progress * 100)}%
        </span>
        <span className="truncate font-mono text-[10px] text-text-faint">
          {job.job_id}
        </span>
      </div>
    </div>
  )
}
