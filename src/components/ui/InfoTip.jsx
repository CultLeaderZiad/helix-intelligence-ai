import { useState, useRef, useEffect } from "react"
import { createPortal } from "react-dom"
import { Info } from "lucide-react"

/**
 * Plain-language explainer for stats and jargon. One short sentence,
 * written for someone who has never used an ad-analytics tool.
 *
 * Uses React portal to render at root level so parent containers
 * (with overflow: hidden or overflow-y: auto) never truncate or cut off text.
 */
export function InfoTip({ text, label = "What does this mean?", align = "auto" }) {
  const [open, setOpen] = useState(false)
  const buttonRef = useRef(null)
  const [coords, setCoords] = useState(null)

  const updatePosition = () => {
    if (!buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const tooltipWidth = 280
    const margin = 16

    let top = rect.top - 8
    const placeBelow = rect.top < 90
    if (placeBelow) {
      top = rect.bottom + 8
    }

    let left = rect.left + rect.width / 2
    let transformX = "-50%"

    if (align === "right" || (align === "auto" && rect.right + tooltipWidth / 2 > window.innerWidth - margin)) {
      left = Math.min(rect.right, window.innerWidth - margin)
      transformX = "-100%"
    } else if (align === "left" || (align === "auto" && rect.left - tooltipWidth / 2 < margin)) {
      left = Math.max(rect.left, margin)
      transformX = "0"
    }

    setCoords({
      top,
      left,
      transform: `translate(${transformX}, ${placeBelow ? "0" : "-100%"})`,
    })
  }

  useEffect(() => {
    if (open) {
      updatePosition()
      window.addEventListener("scroll", updatePosition, true)
      window.addEventListener("resize", updatePosition)
      return () => {
        window.removeEventListener("scroll", updatePosition, true)
        window.removeEventListener("resize", updatePosition)
      }
    }
  }, [open])

  return (
    <span className="relative inline-flex items-center">
      <button
        ref={buttonRef}
        type="button"
        aria-label={label}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-sm text-text-faint transition-colors hover:text-text focus:outline-none"
      >
        <Info className="h-3 w-3 shrink-0" aria-hidden="true" />
      </button>

      {open && coords && typeof document !== "undefined"
        ? createPortal(
            <span
              role="tooltip"
              style={{
                position: "fixed",
                top: `${coords.top}px`,
                left: `${coords.left}px`,
                transform: coords.transform,
              }}
              className="pointer-events-none z-[9999] w-[280px] max-w-[90vw] whitespace-normal break-words rounded border border-border/80 bg-surface-3 p-2.5 text-left text-xs font-normal normal-case leading-relaxed text-text shadow-2xl backdrop-blur-sm animate-in fade-in zoom-in-95 duration-100"
            >
              {text}
            </span>,
            document.body
          )
        : null}
    </span>
  )
}

export default InfoTip

