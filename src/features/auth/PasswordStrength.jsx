import { cn } from "@/lib/utils"
import { ProgressBar } from "@/components/ui/ProgressBar"
import { scorePassword } from "./validation"
import { useLanguage } from "@/context/LanguageContext"

/**
 * Password-strength readout built from the existing `ProgressBar` and the
 * app's mono label vocabulary — not a bespoke rainbow bar. The bar encodes
 * magnitude (0..1); the mono tier word carries the judgement in a
 * functional colour. Tone is reserved for meaning, as everywhere else.
 */
const TIERS = [
  { key: null, fallback: "—", tone: "muted", text: "text-text-faint" },
  { key: "authStrengthWeak", fallback: "Weak", tone: "danger", text: "text-danger" },
  { key: "authStrengthFair", fallback: "Fair", tone: "warning", text: "text-warning" },
  { key: "authStrengthGood", fallback: "Good", tone: "warning", text: "text-warning" },
  { key: "authStrengthStrong", fallback: "Strong", tone: "success", text: "text-success" },
]

export function PasswordStrength({ value = "", className = "" }) {
  const { t } = useLanguage()
  const score = scorePassword(value)
  const tier = TIERS[score]

  return (
    <div className={cn("flex flex-col gap-1.5", className)} aria-live="polite">
      <ProgressBar value={score / 4} tone={tier.tone} />
      <div className="flex items-center justify-between">
        <span className="label-mono">{t("authPasswordStrength", "Password strength")}</span>
        <span
          className={cn(
            "font-mono text-[10px] uppercase leading-none tracking-[0.08em]",
            tier.text,
          )}
        >
          {tier.key ? t(tier.key, tier.fallback) : tier.fallback}
        </span>
      </div>
    </div>
  )
}
