import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import ReflectiveCard from "@/components/ui/ReflectiveCard/ReflectiveCard"

const CARD_WIDTH = 300

/** USD shown the same way in both languages ("$29"), so prices never reorder in RTL. */
export function formatPrice(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value)
}

/**
 * One plan as a metal card: badge, name, price, trial note, tagline, features, call to action.
 * @param {{
 *   badge: string, status?: string, statusColor?: string, name: string, price?: string,
 *   period?: string, tagline?: string, trialNote?: string, features: string[], cta: string, to: string,
 *   onSelect?: () => void, busy?: boolean, highlight?: boolean,
 * }} props
 */
export function PlanCard({ badge, status, statusColor = "#d4ff00", name, price, period, tagline, trialNote, features, cta, to, onSelect, busy = false, highlight }) {
  const ctaClass = `mt-auto inline-flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:opacity-60 ${
    highlight ? "bg-accent text-black hover:brightness-110" : "border border-white/15 bg-white/10 text-white hover:bg-white/15"
  }`
  return (
    <ReflectiveCard
      width={CARD_WIDTH}
      height="auto"
      radius={24}
      tint={highlight ? "#eaffb0" : "#ffffff"}
      shine={highlight ? 1.3 : 1}
      glare={0.5}
      intro
      style={{ minHeight: 520 }}
    >
      <div className="flex h-full min-h-[480px] flex-col gap-4 text-start">
        <div className="reflective-card__header">
          <span className="reflective-card__badge">{badge}</span>
          {status ? (
            <span className="reflective-card__status">
              <span className="reflective-card__dot" style={{ background: statusColor }} />
              {status}
            </span>
          ) : null}
        </div>

        <div>
          <h2 className="reflective-card__name" dir="auto">{name}</h2>
          {price ? (
            <p className="mt-2 flex items-baseline gap-1.5">
              <span className="text-3xl font-semibold tracking-tight text-[var(--rc-ink)]" dir="ltr">{price}</span>
              {period ? <span className="text-sm text-[var(--rc-muted)]">{period}</span> : null}
            </p>
          ) : null}
          {trialNote ? <p className="mt-1 text-xs font-medium text-accent" dir="auto">{trialNote}</p> : null}
          {tagline ? <p className="reflective-card__role mt-2" dir="auto">{tagline}</p> : null}
        </div>

        <ul className="flex flex-1 flex-col gap-2 text-sm text-[var(--rc-ink)]">
          {features.map((feature) => (
            <li key={feature} className="flex items-start gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
              <span dir="auto">{feature}</span>
            </li>
          ))}
        </ul>

        {onSelect ? (
          <button type="button" onClick={onSelect} disabled={busy} aria-busy={busy} className={ctaClass}>
            {cta}
          </button>
        ) : (
          <Link to={to} className={ctaClass}>
            {cta}
          </Link>
        )}
      </div>
    </ReflectiveCard>
  )
}

export default PlanCard
