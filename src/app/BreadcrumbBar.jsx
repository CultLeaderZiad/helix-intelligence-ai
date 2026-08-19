import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Top breadcrumb strip. Purely presentational: a page passes the trail it
 * occupies and, optionally, controls for the right-hand slot. It never
 * derives its own labels from the router so a page can name a transient
 * context (a job, a creative) that no route knows about.
 */
export function BreadcrumbBar({ trail = [], meta, actions, className }) {
  return (
    <div
      className={cn(
        "flex h-9 shrink-0 items-center gap-2 border-b border-border bg-surface px-3",
        className,
      )}
    >
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5">
        {trail.map((segment, i) => {
          const last = i === trail.length - 1
          return (
            <span key={segment} className="flex min-w-0 items-center gap-1.5">
              {i > 0 ? (
                <ChevronRight
                  className="h-3 w-3 shrink-0 text-text-faint"
                  aria-hidden="true"
                />
              ) : null}
              <span
                aria-current={last ? "page" : undefined}
                className={cn(
                  "truncate text-[13px]",
                  last ? "text-text" : "text-text-muted",
                )}
              >
                {segment}
              </span>
            </span>
          )
        })}
      </nav>

      {meta ? (
        <>
          <span className="h-3 w-px shrink-0 bg-border" aria-hidden="true" />
          <span className="label-mono truncate">{meta}</span>
        </>
      ) : null}

      {actions ? <div className="ml-auto flex items-center gap-1.5">{actions}</div> : null}
    </div>
  )
}
