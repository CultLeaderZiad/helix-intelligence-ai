import { cn } from "@/lib/utils"

/** 1px border on a raised surface. No shadow, no gradient, ever. */
export function Panel({ className, children, ...props }) {
  return (
    <div
      className={cn("border border-border bg-surface rounded-sm", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function PanelHeader({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "flex h-9 shrink-0 items-center justify-between gap-2 border-b border-border px-3",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function PanelTitle({ className, children, ...props }) {
  return (
    <h2 className={cn("label-mono text-text", className)} {...props}>
      {children}
    </h2>
  )
}

export function PanelBody({ className, children, ...props }) {
  return (
    <div className={cn("p-3", className)} {...props}>
      {children}
    </div>
  )
}
