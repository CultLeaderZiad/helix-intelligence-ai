import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"

/**
 * Pricing — priced by loop volume, not seats, because the product's unit of
 * work is a scrape/scoring run. One accent tier only; every other surface
 * stays on the hairline/surface palette so the recommended plan is the sole
 * thing the eye lands on.
 */
const TIERS = [
  {
    key: "analyst",
    name: "Analyst",
    price: "$49",
    cadence: "/ mo",
    blurb: "For a single operator running discovery.",
    features: [
      "120 discovery runs / mo",
      "30-day corpus retention",
      "Composite scoring",
      "1 seat",
    ],
    cta: "Start free trial",
    featured: false,
  },
  {
    key: "team",
    name: "Team",
    price: "$199",
    cadence: "/ mo",
    blurb: "For teams closing the full loop.",
    features: [
      "1,000 discovery runs / mo",
      "Unlimited corpus retention",
      "Intelligence mining",
      "Creative briefs",
      "5 seats",
    ],
    cta: "Start free trial",
    featured: true,
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "Custom",
    cadence: "",
    blurb: "For agencies operating at scale.",
    features: [
      "Unlimited runs",
      "API access & webhooks",
      "SSO / SAML",
      "Dedicated SLA",
      "Unlimited seats",
    ],
    cta: "Contact sales",
    featured: false,
  },
]

export function PricingSection() {
  return (
    <section id="pricing" className="scroll-mt-16 border-b border-border">
      <div className="mx-auto w-full max-w-6xl px-4 py-20 md:px-6">
        <div className="flex flex-col gap-3 md:max-w-2xl">
          <span className="font-mono text-[10px] uppercase leading-none tracking-[0.14em] text-accent-dim">
            Pricing
          </span>
          <h2 className="text-balance text-2xl font-medium tracking-tight text-text md:text-3xl">
            Priced by the loop, not the seat.
          </h2>
          <p className="text-pretty text-sm leading-relaxed text-text-muted">
            Every plan runs the full instrument. What scales is how much of the
            web you point it at.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          {TIERS.map((tier) => (
            <div
              key={tier.key}
              className={cn(
                "flex flex-col rounded-sm border bg-surface p-6",
                tier.featured ? "border-accent" : "border-border",
              )}
            >
              <div className="flex items-center justify-between">
                <h3 className="font-mono text-sm font-medium uppercase tracking-[0.08em] text-text">
                  {tier.name}
                </h3>
                {tier.featured ? (
                  <span className="label-mono text-accent-dim">recommended</span>
                ) : null}
              </div>

              <div className="mt-4 flex items-baseline gap-1.5">
                <span className="tnum font-mono text-3xl font-medium leading-none text-text">
                  {tier.price}
                </span>
                {tier.cadence ? (
                  <span className="font-mono text-xs text-text-faint">
                    {tier.cadence}
                  </span>
                ) : null}
              </div>

              <p className="mt-3 text-[13px] leading-relaxed text-text-muted">
                {tier.blurb}
              </p>

              <ul className="mt-6 flex flex-col gap-2.5 border-t border-border pt-6">
                {tier.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-2 text-[13px] leading-relaxed text-text"
                  >
                    <Check
                      className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-dim"
                      aria-hidden="true"
                    />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button
                as={Link}
                to="/sign-up"
                variant={tier.featured ? "primary" : "outline"}
                size="lg"
                className="mt-6 w-full"
              >
                {tier.cta}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
