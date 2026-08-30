import { ChevronRight, ChevronLeft } from "lucide-react"
import { cn } from "@/lib/utils"
import { LanguageSwitcher } from "@/components/LanguageSwitcher"
import { useLanguage } from "@/context/LanguageContext"

export function BreadcrumbBar({ trail = [], meta, actions, className }) {
  const { t, isRtl } = useLanguage()

  const ChevronIcon = isRtl ? ChevronLeft : ChevronRight

  return (
    <div
      className={cn(
        "flex h-11 shrink-0 items-center gap-3 border-b border-border bg-surface px-4 shadow-xs select-none",
        className,
      )}
    >
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2">
        {trail.map((segment, i) => {
          const last = i === trail.length - 1
          const translatedSegment = t(segment.toLowerCase(), segment)
          return (
            <span key={segment} className="flex min-w-0 items-center gap-1.5">
              {i > 0 ? (
                <ChevronIcon
                  className="h-3.5 w-3.5 shrink-0 text-text-faint"
                  aria-hidden="true"
                />
              ) : null}
              <span
                aria-current={last ? "page" : undefined}
                className={cn(
                  "truncate text-[13px] font-medium",
                  last ? "text-text font-bold" : "text-text-muted",
                )}
              >
                {translatedSegment}
              </span>
            </span>
          )
        })}
      </nav>

      {meta ? (
        <>
          <span className="h-3 w-px shrink-0 bg-border" aria-hidden="true" />
          <span className="label-mono truncate text-text-muted">{meta}</span>
        </>
      ) : null}

      <div className="ml-auto flex items-center gap-2.5">
        {actions ? <div className="flex items-center gap-1.5">{actions}</div> : null}
        <LanguageSwitcher />
      </div>
    </div>
  )
}

export default BreadcrumbBar
