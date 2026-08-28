import { cn } from "@/lib/utils"
import { Button } from "./Button"

/**
 * Loading / empty / error are first-class components, not afterthoughts.
 * Every data surface in the app must render one of these three.
 */

export function Skeleton({ className, ...props }) {
  return <div className={cn("animate-pulse bg-surface-2", className)} {...props} />
}

/**
 * Row-shaped skeleton. Column widths and row height mirror ResultsTable
 * exactly, so nothing reflows when the real set lands — a loading state
 * that changes the layout is worse than no loading state.
 *
 * Rows fade toward the fold rather than pulsing in unison: the eye reads
 * one incoming set instead of ten independent blinks.
 */
export function SkeletonRows({ rows = 8, className }) {
  return (
    <div className={cn("min-w-0 flex-1 overflow-hidden", className)} aria-hidden="true">
      {/* Header placeholder keeps the sticky column band present. */}
      <div className="flex h-[33px] items-center gap-2 border-b border-border-strong bg-surface px-3">
        <Skeleton className="h-2 w-16" />
        <Skeleton className="ml-auto h-2 w-10" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex min-w-[720px] items-center gap-2 border-b border-border px-3 py-2"
          style={{ opacity: Math.max(0.15, 1 - i * 0.1) }}
        >
          {/* Creative: headline over domain, the two-line cell */}
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-3 w-[62%]" />
            <Skeleton className="h-2 w-[34%]" />
          </div>
          <Skeleton className="h-3 w-[104px] shrink-0" />
          <Skeleton className="h-4 w-[72px] shrink-0" />
          <Skeleton className="h-[3px] w-[112px] shrink-0" />
          <Skeleton className="h-3 w-[64px] shrink-0" />
          <Skeleton className="h-3 w-[52px] shrink-0" />
          <Skeleton className="h-3 w-[52px] shrink-0" />
          <Skeleton className="h-3 w-[60px] shrink-0" />
        </div>
      ))}
    </div>
  )
}

/**
 * Shared frame for the three terminal states so empty and error are
 * visibly siblings: hairline grid backdrop, a mono status line, a
 * sentence, an action. Hierarchy comes from the type scale alone — the
 * layout still reads correctly with colour removed.
 */
function StateFrame({
  status,
  statusTone,
  title,
  description,
  action,
  meta,
  icon: Icon,
  className,
}) {
  return (
    <div
      className={cn(
        "grid-backdrop flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16",
        className,
      )}
    >
      <div className="flex w-full max-w-sm flex-col gap-3 border border-border bg-surface p-4">
        <div className="flex items-baseline justify-between gap-3">
          <span className={cn("label-mono flex items-center gap-1.5", statusTone)}>
            {Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null}
            {status}
          </span>
          {meta ? <span className="label-mono tnum truncate">{meta}</span> : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <p className="text-pretty text-[13px] font-medium leading-snug text-text">
            {title}
          </p>
          {description ? (
            <p className="text-pretty text-xs leading-relaxed text-text-muted">
              {description}
            </p>
          ) : null}
        </div>

        {action ? <div className="flex items-center gap-1.5 pt-0.5">{action}</div> : null}
      </div>
    </div>
  )
}

export function EmptyState({
  status = "no data",
  title,
  description,
  action,
  icon,
  className,
}) {
  return (
    <StateFrame
      status={status}
      statusTone="text-text-faint"
      title={title}
      description={description}
      action={action}
      icon={icon}
      className={className}
    />
  )
}

export function ErrorState({ error, onRetry, className, description }) {
  const message =
    error?.message ?? "The request failed for a reason the client did not recognise."
  const code = error?.code ?? error?.status

  return (
    <StateFrame
      status="request failed"
      statusTone="text-danger"
      meta={code ? String(code) : null}
      title={message}
      description={description ?? "Nothing was written and no partial set was kept. Retrying re-runs the same request with the same parameters."}
      action={
        onRetry ? (
          <Button size="sm" variant="outline" onClick={onRetry}>
            Retry
          </Button>
        ) : null
      }
      className={className}
    />
  )
}
