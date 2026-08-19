import { cn } from "@/lib/utils"
import { formatRelative } from "@/lib/format"

/**
 * System-health panel: one row per monitored dependency, each with a
 * status dot bound directly to a design token (success / warning /
 * danger) and its last-probe timestamp. The dot is the load-bearing
 * signal; the words beside it stay neutral so colour reads at a glance
 * down the column.
 */

const DOT_TONE = {
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
}

export function SystemHealthPanel({ services }) {
  return (
    <ul className="flex flex-col">
      {services.map((service, i) => (
        <li
          key={service.id}
          className={cn(
            "flex items-center gap-3 px-3 py-2.5",
            i > 0 ? "border-t border-border" : null,
          )}
        >
          <span
            className={cn(
              "h-2 w-2 shrink-0 rounded-full",
              DOT_TONE[service.status] ?? "bg-border-strong",
              service.status === "danger" ? "animate-pulse" : null,
            )}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] text-text">{service.name}</p>
            <p className="truncate text-[11px] text-text-faint">{service.detail}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-0.5">
            <span className="tnum font-mono text-[11px] text-text-muted">
              {service.latency_ms === null || service.latency_ms === undefined
                ? "—"
                : `${service.latency_ms}ms`}
            </span>
            <span className="label-mono">{formatRelative(service.last_checked)}</span>
          </div>
          <span className="sr-only">{`status: ${service.status}`}</span>
        </li>
      ))}
    </ul>
  )
}
