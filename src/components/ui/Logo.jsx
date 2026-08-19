import { cn } from "@/lib/utils"

/**
 * The Helix mark + wordmark.
 *
 * The glyph is the exact accent clip-path used in the in-app Sidebar, so
 * the public surfaces and the authenticated shell read as one product.
 * The wordmark is set in the mono face, uppercase and letter-spaced —
 * the same technical voice as every `.label-mono` in the UI. No new
 * colour, radius, or font is introduced here.
 */
export function Logo({ showWordmark = true, wordmark = "HELIX", className }) {
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border border-border-strong bg-surface-2">
        <span
          className="h-2.5 w-2.5 bg-accent"
          aria-hidden="true"
          style={{ clipPath: "polygon(0 0, 100% 28%, 100% 100%, 0 72%)" }}
        />
      </span>
      {showWordmark ? (
        <span className="font-mono text-[13px] font-medium tracking-[0.16em] text-text">
          {wordmark}
        </span>
      ) : null}
    </span>
  )
}
