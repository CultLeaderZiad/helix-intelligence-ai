import { useState } from "react"
import { Info } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Plain-language explainer for stats and jargon. One short sentence,
 * written for someone who has never used an ad-analytics tool. Uses
 * only existing tokens — no new colors or shapes.
 */
export function InfoTip({ text, label = "What does this mean?" }) {
  const [open, setOpen] = useState(false)

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-label={label}
        title={text}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-sm text-text-faint transition-colors hover:text-text"
      >
        <Info className="h-3 w-3" aria-hidden="true" />
      </button>
      {open ? (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-40 mb-1.5 w-max max-w-[260px] -translate-x-1/2 rounded border border-border bg-surface-3 p-2 text-left text-xs font-normal normal-case leading-relaxed text-text shadow-lg"
        >
          {text}
        </span>
      ) : null}
    </span>
  )
}

export default InfoTip
