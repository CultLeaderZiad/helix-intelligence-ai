import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Check } from "lucide-react"
import { PublicHeader } from "@/app/PublicHeader"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"
import { SkipToContent } from "@/components/ui/SkipToContent"
import ReflectiveCard from "@/components/ui/ReflectiveCard/ReflectiveCard"
import { accountService, pricingService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { useAsync } from "@/hooks/useAsync"
import { useLanguage } from "@/context/LanguageContext"
import { localized, localizedList, usePricingCopy } from "@/i18n/pricing"

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
 * One plan as a metal card: badge, name, price, tagline, features, call to action.
 * @param {{
 *   badge: string, status?: string, statusColor?: string, name: string, price?: string,
 *   period?: string, tagline?: string, features: string[], cta: string, to: string,
 *   onSelect?: () => void, busy?: boolean, highlight?: boolean,
 * }} props
 */
export function PlanCard({ badge, status, statusColor = "#d4ff00", name, price, period, tagline, features, cta, to, onSelect, busy = false, highlight }) {
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

export function PricingPage() {
  const c = usePricingCopy()
  const { lang } = useLanguage()
  const { data, loading, error } = useAsync(() => pricingService.getPricing(), [])
  const { user } = useAuth()
  const navigate = useNavigate()
  const [checkoutPlan, setCheckoutPlan] = useState(null)
  const [checkoutError, setCheckoutError] = useState(false)

  // Paid plans with Whop checkout. Signed out: sign in first (new visitors sign
  // up from there). Signed in: the server builds the link for the
  // workspace in the session and we leave for Whop.
  async function subscribe(planId) {
    if (!user) {
      navigate("/sign-in")
      return
    }
    setCheckoutError(false)
    setCheckoutPlan(planId)
    try {
      const { checkout_url: url } = await accountService.createCheckout(planId)
      if (!url) throw new Error("no checkout url")
      window.location.assign(url)
    } catch {
      setCheckoutError(true)
      setCheckoutPlan(null)
    }
  }

  // Only the server decides whether a trial exists (SIGNUP_TRIAL_DAYS, default 7; 0 = off).
  const trialDays = Number(data?.trial_days) > 0 ? Number(data.trial_days) : 0
  const trialFeatures = (data?.trial_features?.length ? data.trial_features : ["discover", "swipe_files", "monitors"])
    .map((key) => c.features[key])
    .filter(Boolean)
  const plans = data?.plans ?? []
  const anyCheckout = plans.some((plan) => plan.checkout)

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <SkipToContent targetId="main-content" />
      <PublicHeader />
      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 text-center sm:px-6">
          <p className="font-mono text-xs uppercase tracking-wider text-accent">{c.label}</p>
          <h1 className="mx-auto mt-4 max-w-2xl text-balance text-4xl font-bold tracking-tight text-white sm:text-5xl">{c.title}</h1>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-sm leading-6 text-text-muted">{loading || error ? null : anyCheckout
            ? (trialDays ? c.bodyCheckout.replace(/7/g, String(trialDays)) : c.bodyCheckoutNoTrial)
            : trialDays ? c.body.replace(/7/g, String(trialDays)) : c.bodyNoTrial}</p>

          <div className="mt-12 flex flex-wrap items-stretch justify-center gap-8">
            {trialDays > 0 ? (
              <PlanCard
                badge={c.trialBadge}
                status={c.trialStatus}
                statusColor="#22c55e"
                name={c.trialName(trialDays)}
                price={formatPrice(0)}
                period=""
                tagline={c.trialTagline}
                features={trialFeatures}
                cta={c.startTrial}
                to="/sign-up"
                highlight={!plans.some((p) => p.pricing?.highlight)}
              />
            ) : null}
            {plans.map((plan) => {
              const p = plan.pricing || {}
              const priced = typeof plan.price_monthly === "number" && plan.price_monthly > 0
              return (
                <PlanCard
                  key={plan.id}
                  badge={localized(p.badge, lang) || c.plan}
                  status={p.highlight ? c.popular : ""}
                  name={plan.name}
                  price={priced ? formatPrice(plan.price_monthly) : c.custom}
                  period={priced ? localized(p.period, lang) || c.perMonth : ""}
                  tagline={localized(p.tagline, lang)}
                  features={localizedList(p.features, lang)}
                  cta={plan.checkout ? (checkoutPlan === plan.id ? c.openingCheckout : c.subscribe)
                    : p.cta === "contact" || !trialDays ? c.contact : c.startTrial}
                  to={p.cta === "contact" || !trialDays ? "/support" : "/sign-up"}
                  onSelect={plan.checkout ? () => subscribe(plan.id) : undefined}
                  busy={checkoutPlan === plan.id}
                  highlight={!!p.highlight}
                />
              )
            })}
          </div>

          <p className="mt-8 text-xs text-text-faint" role={error || checkoutError ? "alert" : undefined}>
            {checkoutError ? c.checkoutFailed : loading ? c.loading : error ? c.failed : plans.length === 0 ? c.noPlans : c.footnote}
          </p>
        </section>
      </main>
      <MarketingFooter />
    </div>
  )
}

export default PricingPage
