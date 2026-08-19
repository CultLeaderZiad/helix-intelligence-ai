import { cn } from "@/lib/utils"

/**
 * Determinate progress bar.
 *
 * `value` is 0..1 and comes from job state. There is no indeterminate
 * animation fallback by design — if we do not know the progress, we
 * should not imply that we do.
 */
export function ProgressBar({ value = 0, tone = "accent", className, striped = false }) {
  const pct = Math.max(0, Math.min(100, value * 100))
  const fill = {
    accent: "bg-accent",
    danger: "bg-danger",
    warning: "bg-warning",
    success: "bg-success",
    muted: "bg-border-strong",
  }[tone]

  return (
    <div
      className={cn("h-1 w-full overflow-hidden bg-surface-3", className)}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn(
          "h-full transition-[width] duration-300 ease-out",
          fill,
          striped && "stripe-progress",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
