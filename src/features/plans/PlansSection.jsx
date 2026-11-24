import { PlanCardList } from "./PlanCardList"
import { usePlanCheckout } from "./usePlanCheckout"
import { pricingService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { useAsync } from "@/hooks/useAsync"
import { useLanguage } from "@/context/LanguageContext"
import { usePricingCopy } from "@/i18n/pricing"

/**
 * The plans inside the app (/access): the same cards as the public pricing page,
 * with Subscribe, and a line about where the user's access stands. Both lines
 * come from the server's access state: when it ends (the trial plus its grace
 * hours) or that it already ended.
 */
export function PlansSection({ access, highlightId }) {
  const c = usePricingCopy()
  const { lang } = useLanguage()
  const { user } = useAuth()
  const checkout = usePlanCheckout()
  const { data, loading, error } = useAsync(() => pricingService.getPricing(), [])
  const plans = data?.plans ?? []

  let status = null
  if (access?.status === "approved" && access.expires_at) {
    const when = new Date(access.expires_at)
    if (!Number.isNaN(when.getTime())) status = c.accessUntil(when.toLocaleString(lang === "ar" ? "ar" : "en"))
  } else if (access?.status === "expired") {
    status = c.trialEnded
  }

  if (loading || error || plans.length === 0) return null

  return (
    <section className="space-y-4 border border-border bg-surface p-4" aria-labelledby="plans-title">
      <h2 id="plans-title" className="font-semibold">{c.plansTitle}</h2>
      {status ? <p className="text-sm text-text-muted" role="status">{status}</p> : null}
      <div className="flex flex-wrap items-stretch justify-center gap-6">
        <PlanCardList plans={plans} copy={c} lang={lang} user={user} checkout={checkout} highlightId={highlightId} />
      </div>
      {checkout.failed ? <p role="alert" className="text-sm text-danger">{c.checkoutFailed}</p> : null}
    </section>
  )
}

export default PlansSection
