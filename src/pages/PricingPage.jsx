import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { PublicHeader } from "@/app/PublicHeader"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"
import { SkipToContent } from "@/components/ui/SkipToContent"
import ReflectiveCard from "@/components/ui/ReflectiveCard/ReflectiveCard"
import { pricingService } from "@/services"
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

/** One plan as a metal card: badge, name, price, tagline, features, call to action. */
export function PlanCard({ badge, status, statusColor = "#d4ff00", name, price, period, tagline, features, cta, to, highlight }) {
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

        <Link
          to={to}
          className={`mt-auto inline-flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
            highlight ? "bg-accent text-black hover:brightness-110" : "border border-white/15 bg-white/10 text-white hover:bg-white/15"
          }`}
        >
          {cta}
        </Link>
      </div>
    </ReflectiveCard>
  )
}

export function PricingPage() {
  const c = usePricingCopy()
  const { lang } = useLanguage()
  const { data, loading, error } = useAsync(() => pricingService.getPricing(), [])

  const trialDays = data?.trial_days || 7
  const trialFeatures = (data?.trial_features?.length ? data.trial_features : ["discover", "swipe_files", "monitors"])
    .map((key) => c.features[key])
    .filter(Boolean)
  const plans = data?.plans ?? []

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <SkipToContent targetId="main-content" />
      <PublicHeader />
      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 text-center sm:px-6">
          <p className="font-mono text-xs uppercase tracking-wider text-accent">{c.label}</p>
          <h1 className="mx-auto mt-4 max-w-2xl text-balance text-4xl font-bold tracking-tight text-white sm:text-5xl">{c.title}</h1>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-sm leading-6 text-text-muted">{c.body}</p>

          <div className="mt-12 flex flex-wrap items-stretch justify-center gap-8">
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
                  cta={p.cta === "contact" ? c.contact : c.startTrial}
                  to={p.cta === "contact" ? "/support" : "/sign-up"}
                  highlight={!!p.highlight}
                />
              )
            })}
          </div>

          <p className="mt-8 text-xs text-text-faint" role={error ? "alert" : undefined}>
            {loading ? c.loading : error ? c.failed : plans.length === 0 ? c.noPlans : c.footnote}
          </p>
        </section>
      </main>
      <MarketingFooter />
    </div>
  )
}

export default PricingPage
