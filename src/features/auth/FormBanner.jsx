import { cn } from "@/lib/utils"

const TONES = {
  danger: { edge: "border-danger/40", status: "text-danger" },
  success: { edge: "border-success/40", status: "text-success" },
  info: { edge: "border-info/40", status: "text-info" },
}

/**
 * Form-level status line for auth errors and confirmations — e.g. "invalid
 * credentials" or "email already registered". Distinct from field errors
 * (which live in the label row): this speaks for the whole submission.
 *
 * Same grammar as the app's terminal states: a mono status tag in the
 * functional colour, then a plain-text sentence. Colour is functional
 * here, never decorative.
 */
export function FormBanner({ tone = "danger", status, children, className }) {
  const t = TONES[tone] ?? TONES.danger
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2.5 rounded-sm border bg-surface-2 px-3 py-2",
        t.edge,
        className,
      )}
    >
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
  )
}
