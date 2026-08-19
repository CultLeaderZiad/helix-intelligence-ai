import { cn } from "@/lib/utils"

/**
 * Rectangular, dense, no pills, no shadows. Accent is reserved for the
 * single primary action on a surface.
 */
const VARIANTS = {
  primary:
    "bg-accent text-[#0A0A0A] hover:bg-accent-dim border border-accent hover:border-accent-dim font-medium",
  default:
    "bg-surface-2 text-text border border-border hover:border-border-strong hover:bg-surface-3",
  ghost:
    "bg-transparent text-text-muted border border-transparent hover:text-text hover:bg-surface-2",
  outline:
    "bg-transparent text-text border border-border hover:border-border-strong hover:bg-surface-2",
  danger:
    "bg-transparent text-danger border border-border hover:border-danger hover:bg-danger/10",
}

const SIZES = {
  xs: "h-6 px-2 text-[11px] gap-1",
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3 text-[13px] gap-1.5",
  lg: "h-9 px-4 text-sm gap-2",
  icon: "h-7 w-7 p-0",
  "icon-sm": "h-6 w-6 p-0",
}

export function Button({
  as: Tag = "button",
  variant = "default",
  size = "md",
  className,
  children,
  ...props
}) {
  return (
    <Tag
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-sm transition-colors duration-100",
        "disabled:pointer-events-none disabled:opacity-40",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  )
}
