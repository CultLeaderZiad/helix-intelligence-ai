import { PublicHeader } from "@/app/PublicHeader"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"
import { SkipToContent } from "@/components/ui/SkipToContent"
import { PlanCard, formatPrice } from "@/features/plans/PlanCard"
import { PlanCardList } from "@/features/plans/PlanCardList"
import { usePlanCheckout } from "@/features/plans/usePlanCheckout"
import { pricingService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { useAsync } from "@/hooks/useAsync"
import { useLanguage } from "@/context/LanguageContext"
import { usePricingCopy } from "@/i18n/pricing"

// Kept as exports: other code and tests import them from here.
export { PlanCard, formatPrice }

export function PricingPage() {
  const c = usePricingCopy()
  const { lang } = useLanguage()
  const { data, loading, error } = useAsync(() => pricingService.getPricing(), [])
  const { user } = useAuth()
  const checkout = usePlanCheckout()

  // Only the server decides whether a trial exists (SIGNUP_TRIAL_DAYS, default 7; 0 = off).
  const trialDays = Number(data?.trial_days) > 0 ? Number(data.trial_days) : 0
  // The default trial card lists exactly what the server grants, nothing more.
  const trialFeatures = (data?.trial_features || []).map((key) => c.features[key]).filter(Boolean)
  const plans = data?.plans ?? []
  const anyCheckout = plans.some((plan) => plan.checkout)
  const anyTrial = trialDays > 0 || plans.some((plan) => Number(plan.trial_days) > 0)

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <SkipToContent targetId="main-content" />
      <PublicHeader />
      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 text-center sm:px-6">
          <p className="font-mono text-xs uppercase tracking-wider text-accent">{c.label}</p>
          <h1 className="mx-auto mt-4 max-w-2xl text-balance text-4xl font-bold tracking-tight text-white sm:text-5xl">{c.title}</h1>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-sm leading-6 text-text-muted">{loading || error ? null : anyCheckout
            ? (anyTrial ? c.bodyCheckout.replace(/7/g, String(trialDays || 7)) : c.bodyCheckoutNoTrial)
            : trialDays ? c.body.replace(/7/g, String(trialDays)) : c.bodyNoTrial}</p>

          <div className="mt-12 flex flex-wrap items-stretch justify-center gap-8">
            {/* With listed plans, each plan card carries its own trial; the default card is for when there are none. */}
            {trialDays > 0 && plans.length === 0 ? (
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
                highlight
              />
            ) : null}
            <PlanCardList plans={plans} copy={c} lang={lang} user={user} checkout={checkout} />
          </div>

          <p className="mt-8 text-xs text-text-faint" role={error || checkout.failed ? "alert" : undefined}>
            {checkout.failed ? c.checkoutFailed : loading ? c.loading : error ? c.failed : plans.length === 0 ? c.noPlans : c.footnote}
          </p>
        </section>
      </main>
      <MarketingFooter />
    </div>
  )
}

export default PricingPage
