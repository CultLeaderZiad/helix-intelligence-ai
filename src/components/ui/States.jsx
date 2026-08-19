import { cn } from "@/lib/utils"
import { Button } from "./Button"

/**
 * Loading / empty / error are first-class components, not afterthoughts.
 * Every data surface in the app must render one of these three.
 */

export function Skeleton({ className, ...props }) {
  return <div className={cn("animate-pulse bg-surface-2", className)} {...props} />
}

/** Row-shaped skeleton so the table does not jump when data lands. */
export function SkeletonRows({ rows = 8, className }) {
  return (
    <div className={cn("flex flex-col", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 border-b border-border px-3 py-2.5"
        >
          <Skeleton className="h-3 w-3 shrink-0 rounded-[2px]" />
          <Skeleton className="h-3 flex-1" style={{ opacity: 1 - i * 0.06 }} />
          <Skeleton className="hidden h-3 w-20 shrink-0 sm:block" />
          <Skeleton className="hidden h-3 w-14 shrink-0 md:block" />
          <Skeleton className="hidden h-3 w-16 shrink-0 lg:block" />
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ icon: Icon, title, description, action, className }) {
  return (
    <div
      className={cn(
        "grid-backdrop flex flex-1 flex-col items-center justify-center gap-3 px-6 py-16 text-center",
        className,
      )}
    >
      {Icon ? (
        <div className="flex h-9 w-9 items-center justify-center border border-border bg-surface">
          <Icon className="h-4 w-4 text-text-faint" aria-hidden="true" />
        </div>
      ) : null}
      <div className="flex flex-col gap-1.5">
        <p className="text-[13px] font-medium text-text">{title}</p>
        {description ? (
          <p className="max-w-sm text-pretty text-xs leading-relaxed text-text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry, className }) {
  const message =
    error?.message ?? "The request failed for a reason the client did not recognise."
  const code = error?.code ?? error?.status

  return (
    <div
      className={cn(
        "flex flex-1 flex-col items-center justify-center gap-3 px-6 py-16 text-center",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-2">
        <span className="label-mono text-danger">
          Request failed{code ? ` · ${code}` : ""}
        </span>
        <p className="max-w-md text-pretty text-[13px] leading-relaxed text-text">
          {message}
        </p>
      </div>
      {onRetry ? (
        <Button size="sm" variant="outline" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  )
}
