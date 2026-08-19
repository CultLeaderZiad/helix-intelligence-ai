import { cn } from "@/lib/utils"
import { scoreFillClass, scoreTextClass } from "@/lib/score"
import { formatScore } from "@/lib/format"

/** Tabular-nums readout. Numbers must never shift width between renders. */
export function MetricValue({ value, unit, className, muted, ...props }) {
  return (
    <span
      className={cn(
        "tnum font-mono text-[13px]",
        muted ? "text-text-muted" : "text-text",
        className,
      )}
      {...props}
    >
      {value}
      {unit ? <span className="ml-0.5 text-[10px] text-text-faint">{unit}</span> : null}
    </span>
  )
}

/**
 * Thin score bar. Accent fill appears only above the "strong" threshold,
 * so a page of accent means something rather than nothing.
 */
export function ScoreBar({ value, max = 10, showValue = true, className, width = "w-14" }) {
  const pct =
    value === null || value === undefined ? 0 : Math.max(0, Math.min(100, (value / max) * 100))

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className={cn("h-[3px] shrink-0 bg-surface-3", width)}
        role="meter"
        aria-valuenow={value ?? 0}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label="Score"
      >
        <div
          className={cn("h-full transition-[width] duration-200", scoreFillClass(value))}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showValue ? (
        <span className={cn("tnum font-mono text-[11px]", scoreTextClass(value))}>
          {formatScore(value)}
        </span>
      ) : null}
    </div>
  )
}

/** Label-over-value stat block for detail surfaces. */
export function StatBlock({ label, value, unit, className }) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="label-mono">{label}</span>
      <MetricValue value={value} unit={unit} />
    </div>
  )
}
