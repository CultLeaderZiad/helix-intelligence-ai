import { cn } from "@/lib/utils"

const TONES = {
  /** On a normal surface. */
  default: "border-border bg-surface-2 text-text-muted",
  /** Sitting on the accent fill of a primary button — inverted. */
  "on-accent": "border-bg/25 bg-bg/10 text-bg",
}

/** Keyboard affordance. Present because this UI expects to be driven by keys. */
export function KeyHint({ tone = "default", children, className }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-4 min-w-4 items-center justify-center rounded-[2px] border px-1",
        "font-mono text-[10px] leading-none",
        TONES[tone],
        className,
      )}
    >
      {children}
    </kbd>
  )
}
