import { useW9Copy } from "@/i18n/w9Product"

/** Metapi record meter for Access & Usage. Shows only what the API returned. */
export function RecordMeter({ usage, error }) {
  const w9 = useW9Copy()
  if (error || !usage) {
    return (
      <div className="space-y-2 border border-border bg-surface p-4 text-sm">
        <h2 className="font-semibold">{w9.recordsTitle}</h2>
        <p className="text-text-muted">{error ? w9.recordsUnavailable : "…"}</p>
      </div>
    )
  }
  const tone = usage.reached ? "bg-danger" : usage.warning ? "bg-warning" : "bg-accent"
  return (
    <div className="space-y-2 border border-border bg-surface p-4 text-sm" data-testid="record-meter">
      <h2 className="font-semibold">{w9.recordsTitle}</h2>
      <p>{w9.recordsUsed(usage.used, usage.cap)} · {w9.recordsRemaining(usage.remaining)}</p>
      <div
        role="meter"
        aria-label={w9.recordsTitle}
        aria-valuemin={0}
        aria-valuemax={usage.cap}
        aria-valuenow={Math.min(usage.used, usage.cap)}
        className="h-2 w-full overflow-hidden rounded-sm bg-bg"
      >
        <div className={`h-full ${tone}`} style={{ width: `${usage.percent}%` }} />
      </div>
      {usage.reached ? (
        <p role="alert" className="text-danger">{w9.recordsReached}</p>
      ) : usage.warning ? (
        <p role="alert" className="text-warning">{w9.recordsWarning}</p>
      ) : null}
      <p className="text-text-muted">{w9.recordsExplain(usage.estimates?.discover_search)}</p>
      <p className="text-text-faint">{w9.recordsResets(usage.period_start)}</p>
    </div>
  )
}

export default RecordMeter
