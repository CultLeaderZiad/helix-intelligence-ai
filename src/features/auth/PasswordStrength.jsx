import { cn } from "@/lib/utils"
import { ProgressBar } from "@/components/ui/ProgressBar"
import { scorePassword } from "./validation"

/**
 * Password-strength readout built from the existing `ProgressBar` and the
 * app's mono label vocabulary — not a bespoke rainbow bar. The bar encodes
 * magnitude (0..1); the mono tier word carries the judgement in a
 * functional colour. Tone is reserved for meaning, as everywhere else.
 */
const TIERS = [
  { label: "—", tone: "muted", text: "text-text-faint" },
  { label: "weak", tone: "danger", text: "text-danger" },
  { label: "fair", tone: "warning", text: "text-warning" },
  { label: "good", tone: "warning", text: "text-warning" },
  { label: "strong", tone: "success", text: "text-success" },
]

export function PasswordStrength({ value = "", className }) {
  const score = scorePassword(value)
  const tier = TIERS[score]

  return (
    <div className={cn("flex flex-col gap-1.5", className)} aria-live="polite">
      <ProgressBar value={score / 4} tone={tier.tone} />
      <div className="flex items-center justify-between">
        <span className="label-mono">password strength</span>
        <span
          className={cn(
            "font-mono text-[10px] uppercase leading-none tracking-[0.08em]",
            tier.text,
          )}
        >
          {tier.label}
        </span>
      </div>
    </div>
  )
}
