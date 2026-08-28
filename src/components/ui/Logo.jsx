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
      <img
        src="/brand/helix-logo.png"
        alt="Helix Logo"
        className="h-5 w-5 shrink-0 rounded-[3px] object-contain"
      />
      {showWordmark ? (
        <span className="font-mono text-[13px] font-medium tracking-[0.16em] text-text">
          {wordmark}
        </span>
      ) : null}
    </span>
  )
}
