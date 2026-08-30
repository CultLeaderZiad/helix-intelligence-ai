import { cn } from "@/lib/utils"

const TONES = {
  danger: { edge: "border-danger/40", status: "text-danger" },
  success: { edge: "border-success/40", status: "text-success" },
  info: { edge: "border-info/40", status: "text-info" },
  warning: { edge: "border-amber-500/40", status: "text-amber-500" },
}

/**
 * Form-level status line for auth errors, service waking notifications,
 * and confirmations. Distinct from field errors: this speaks for the whole submission.
 */
export function FormBanner({ tone = "danger", status, children, action, className }) {
  const t = TONES[tone] ?? TONES.danger
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start justify-between gap-2.5 rounded-sm border bg-surface-2 px-3 py-2",
        t.edge,
        className,
      )}
    >
      <div className="flex flex-1 items-start gap-2.5 min-w-0">
        {status ? (
          <span
            className={cn(
              "mt-px shrink-0 font-mono text-[10px] uppercase leading-none tracking-[0.08em]",
              t.status,
            )}
          >
            {status}
          </span>
        ) : null}
        <p className="text-[12px] leading-relaxed text-text">{children}</p>
      </div>
      {action ? <div className="shrink-0 pt-0.5">{action}</div> : null}
    </div>
  )
}
