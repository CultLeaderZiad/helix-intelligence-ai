import { cn } from "@/lib/utils"

/** Keyboard affordance. Present because this UI expects to be driven by keys. */
export function KeyHint({ children, className }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-4 min-w-4 items-center justify-center rounded-[2px] border border-border bg-surface-2 px-1",
        "font-mono text-[10px] leading-none text-text-muted",
        className,
      )}
    >
      {children}
    </kbd>
  )
}
