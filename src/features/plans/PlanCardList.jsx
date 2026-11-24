import { localized } from "@/i18n/pricing"
import { PlanCard, formatPrice } from "./PlanCard"
import { featureLines, limitLines } from "./planDetails"

/**
 * The listed plans as cards, shared by the public pricing page and the in-app
 * plans page. Every value comes from the plan row: price, trial length,
 * features and limits.
 * - Signed out: "Start your N-day free trial" opens sign-up with the chosen
 *   plan, so the new account gets that plan's features for the trial.
 * - Signed in: "Subscribe" opens the server-created payment page.
 */
/** @param {{ plans: any[], copy: any, lang: string, user: any, checkout: any, highlightId?: string }} props */
export function PlanCardList({ plans, copy: c, lang, user, checkout, highlightId }) {
  return plans.map((plan) => {
    const p = plan.pricing || {}
    const priced = typeof plan.price_monthly === "number" && plan.price_monthly > 0
    const trialDays = Number(plan.trial_days) > 0 ? Number(plan.trial_days) : 0
    const contact = p.cta === "contact"
    const canSubscribe = Boolean(user) && plan.checkout && !contact
    let cta
    let to
    let onSelect
    if (contact || (user && !canSubscribe)) {
      cta = c.contact
      to = "/support"
    } else if (canSubscribe) {
      cta = checkout.busyId === plan.id ? c.openingCheckout : c.subscribe
      to = "/access"
      onSelect = () => checkout.subscribe(plan.id)
    } else {
      cta = trialDays ? c.startTrialDays(trialDays) : c.getStarted
      to = `/sign-up?plan=${encodeURIComponent(plan.id)}`
    }
    return (
      <PlanCard
        key={plan.id}
        badge={localized(p.badge, lang) || c.plan}
        status={p.highlight ? c.popular : ""}
        name={plan.name}
        price={priced ? formatPrice(plan.price_monthly) : c.custom}
        period={priced ? localized(p.period, lang) || c.perMonth : ""}
        tagline={localized(p.tagline, lang)}
        trialNote={trialDays && !contact ? c.trialNote(trialDays) : undefined}
        features={[...featureLines(plan, lang, c), ...limitLines(plan.limits, c.limitLabels)]}
        cta={cta}
        to={to}
        onSelect={onSelect}
        busy={checkout.busyId === plan.id}
        highlight={plan.id === highlightId || (!highlightId && !!p.highlight)}
      />
    )
  })
}

export default PlanCardList
