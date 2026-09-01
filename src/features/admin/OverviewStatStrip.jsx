import { Building2, Loader2, ShieldCheck, AlertTriangle, CircleDollarSign, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatInt, formatPercent } from "@/lib/format"

/**
 * Overview status strip. A dense, evenly-weighted row of measured
 * counters — the operator's first glance. Every value is passed in from
 * the service via the page's hook; nothing here is computed or invented.
 *
 * Tone is reserved: the health cell and an out-of-band error rate are the
 * only cells that carry colour, so a red readout means something.
 */

const HEALTH_PRESENTATION = {
  operational: { label: "Operational", tone: "text-success", dot: "bg-success" },
  degraded: { label: "Degraded", tone: "text-warning", dot: "bg-warning" },
  down: { label: "Down", tone: "text-danger", dot: "bg-danger" },
}

/** Error rate is a judgement, not just a number: colour the threshold. */
function errorRateTone(rate) {
  if (rate >= 2) return "text-danger"
  if (rate >= 1) return "text-warning"
  return "text-text"
}

function Cell({ label, icon: Icon, children, className }) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-1 flex-col gap-2 border-border px-4 py-3",
        "border-b sm:border-b-0 sm:border-r sm:last:border-r-0",
        className,
      )}
    >
      <span className="label-mono flex items-center gap-1.5">
        {Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null}
        {label}
      </span>
      {children}
    </div>
  )
}

export function OverviewStatStrip({ stats }) {
  const health = HEALTH_PRESENTATION[stats.system_health] ?? HEALTH_PRESENTATION.down

  return (
    <div className="flex flex-col border border-border bg-surface rounded-sm sm:flex-row sm:flex-wrap">
      <Cell label="Organizations" icon={Building2}>
        <span className="tnum font-mono text-2xl leading-none text-text">
          {formatInt(stats.organizations)}
        </span>
      </Cell>

      <Cell label="Active scrape jobs" icon={Loader2}>
        <span className="tnum flex items-baseline gap-2 font-mono text-2xl leading-none text-text">
          {formatInt(stats.active_scrape_jobs)}
          {stats.active_scrape_jobs > 0 ? (
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent animate-pulse" aria-hidden="true" />
          ) : null}
        </span>
      </Cell>

      <Cell label="System health" icon={stats.system_health === "operational" ? ShieldCheck : AlertTriangle}>
        <span className={cn("flex items-center gap-2 text-2xl leading-none", health.tone)}>
          <span className={cn("h-2 w-2 shrink-0 rounded-full", health.dot)} aria-hidden="true" />
          <span className="text-[15px] font-medium">{health.label}</span>
        </span>
      </Cell>

      <Cell label={`API error rate · ${stats.window_label}`} icon={AlertTriangle}>
        <span className={cn("tnum font-mono text-2xl leading-none", errorRateTone(stats.api_error_rate))}>
          {formatPercent(stats.api_error_rate, 2)}
        </span>
      </Cell>

      <Cell label="API Calls (Today)" icon={Activity}>
        <span className="tnum font-mono text-2xl leading-none text-text">
          {formatInt(stats.today_api_calls)}
        </span>
      </Cell>

      <Cell label="Est. API Spend (Today)" icon={CircleDollarSign}>
        <span className="tnum font-mono text-2xl leading-none text-text">
          ${Number(stats.today_api_spend || 0).toFixed(4)}
        </span>
      </Cell>
    </div>
  )
}
