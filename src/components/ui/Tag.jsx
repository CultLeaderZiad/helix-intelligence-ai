import { cn } from "@/lib/utils"

const TONES = {
  default: "border-border text-text-muted",
  strong: "border-border-strong text-text",
  accent: "border-accent/40 text-accent bg-accent-wash",
  success: "border-success/30 text-success",
  warning: "border-warning/30 text-warning",
  danger: "border-danger/30 text-danger",
  info: "border-info/30 text-info",
}

/** Mono, uppercase, 10px. The taxonomy marker of this interface. */
export function Tag({ tone = "default", className, children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 border px-1.5 py-0.5 rounded-sm",
        "font-mono text-[10px] uppercase leading-none tracking-[0.06em]",
        TONES[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
