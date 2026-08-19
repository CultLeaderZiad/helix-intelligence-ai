import { Button } from "@/components/ui/Button"
import { formatDuration, formatInt } from "@/lib/format"
import { cn } from "@/lib/utils"
// Pipeline vocabulary, not row data. The service reports stage_index /
// stages_total against this canonical list; the real worker will report
// the same keys. Same class of exception as brandsById in ResultsTable.
import { DISCOVERY_STAGES } from "@/data/jobs"

/**
 * Terminal-style live job readout.
 *
 * Every line is application state: stage completion comes from
 * `job.stage_index`, the streaming record count from `job.records_found`,
 * elapsed time from `job.elapsed_ms`. Nothing here animates unless the
 * poll is actually returning new values — if polling stops, this stops.
 */

/** Dotted leader between a stage label and its status column. */
function Leader() {
  return (
    <span
      aria-hidden="true"
      className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong"
    />
  )
}

function StageLine({ stage, state, records, error }) {
  // state: "done" | "active" | "pending" | "failed"
  const pending = state === "pending"
  return (
    <div
      className={cn(
        "flex items-baseline font-mono text-[11px] leading-5",
        pending ? "text-text-faint" : "text-text-muted",
      )}
    >
      <span className="w-4 shrink-0">
        {state === "active" ? <span className="text-accent">→</span> : null}
        {state === "done" ? "→" : null}
        {state === "failed" ? <span className="text-danger">✕</span> : null}
      </span>
      <span className={cn(state === "active" && "text-text")}>
        {stage.label.toLowerCase()}
      </span>
      {!pending ? <Leader /> : null}
      {state === "done" ? (
        <span className="tnum shrink-0 text-text-muted">
          {records !== null ? formatInt(records) : "ok"}
        </span>
      ) : null}
      {state === "active" ? (
        <span className="tnum shrink-0 text-text">
          {records !== null ? formatInt(records) : null}
          <span className="cursor-blink ml-1 inline-block h-3 w-[7px] translate-y-[2px] bg-accent" />
        </span>
      ) : null}
      {state === "failed" ? (
        <span className="shrink-0 text-danger">err</span>
      ) : null}
      <span className="sr-only">
        {state === "done" ? "complete" : state === "active" ? "in progress" : state}
      </span>
    </div>
  )
}

/** Stages that stream a record count while running. */
const COUNTING_STAGES = new Set(["enumerating", "fetching_assets", "scoring"])

export function JobProgress({ job, query, onCancel }) {
  if (!job) return null

  const failed = job.status === "failed"
  const done = job.status === "succeeded"
  const currentIndex = job.stage_index

  return (
    <div
      className="shrink-0 border-b border-border bg-bg px-3 py-3"
      role="status"
      aria-live="polite"
    >
      {/* Session header */}
      <div className="flex items-center gap-2.5 font-mono text-[11px]">
        <span className="flex items-center gap-1.5">
          <span
            className={cn(
              "h-[7px] w-[7px] rounded-full",
              failed ? "bg-danger" : done ? "bg-success" : "bg-accent animate-pulse",
            )}
            aria-hidden="true"
          />
          <span
            className={cn(
              "label-mono",
              failed ? "text-danger" : done ? "text-success" : "text-accent",
            )}
          >
            {failed ? "failed" : done ? "done" : "live"}
          </span>
        </span>
        <span className="truncate text-text-muted">discover/{job.job_id}</span>
        <span className="tnum ml-auto shrink-0 text-text-faint">
          {formatDuration(job.elapsed_ms)}
        </span>
        {!failed && !done && onCancel ? (
          <Button size="xs" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>

      {/* Command echo. The query is data, not status — it reads at full
          text weight rather than in accent, which is reserved for live
          state and exceptional scores. */}
      <p className="mt-2 truncate font-mono text-[11px] leading-5 text-text-muted">
        <span className="text-text-faint">$ </span>
        query <span className="text-text">&quot;{query?.trim() || "*"}&quot;</span>
      </p>

      {/* Stage transcript */}
      <div className="mt-1 max-w-xl">
        {DISCOVERY_STAGES.map((stage, i) => {
          let state = "pending"
          if (failed && i === currentIndex) state = "failed"
          else if (i < currentIndex || done) state = "done"
          else if (i === currentIndex) state = "active"

          const counts = COUNTING_STAGES.has(stage.key)
          const records =
            counts && (state === "done" || state === "active")
              ? job.records_found
              : null

          if (failed && i > currentIndex) return null

          return (
            <StageLine
              key={stage.key}
              stage={stage}
              state={state}
              records={records}
              error={job.error}
            />
          )
        })}

        {failed ? (
          <p className="mt-1 font-mono text-[11px] leading-5 text-danger">
            * {job.error ?? "job failed"}
          </p>
        ) : null}

        {done ? (
          <p className="mt-1 font-mono text-[11px] leading-5 text-success">
            * complete — {formatInt(job.records_found)} creatives indexed
          </p>
        ) : null}
      </div>
    </div>
  )
}
