import { Link } from "react-router-dom"
import { ArrowLeft, ArrowRight, ShieldCheck } from "lucide-react"
import { useLanguage } from "@/context/LanguageContext"

export function PricingSection() {
  const { t, isRtl } = useLanguage()

  return (
    <section className="border-y border-white/[0.08] bg-[#07070a] px-6 py-16 text-white sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-4xl flex-col gap-6 rounded-xl border border-white/10 bg-white/[0.025] p-6 sm:p-8 md:flex-row md:items-center md:justify-between">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 text-accent">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            <p className="font-mono text-xs uppercase tracking-wider">{t("marketingPricingTitle")}</p>
          </div>
          <h2 className="mt-4 text-2xl font-bold">{t("marketingPricingTitle")}</h2>
          <p className="mt-3 text-sm leading-6 text-text-muted">{t("marketingPricingBody")}</p>
          <p className="mt-2 text-sm leading-6 text-text-muted">{t("marketingNoCheckout")}</p>
          <p className="mt-2 text-sm leading-6 text-text-muted">{t("marketingAdminGrant")}</p>
        </div>
        <Link to="/sign-in" className="inline-flex shrink-0 items-center gap-2 text-sm font-semibold text-accent hover:text-white">
          {t("marketingSignIn")}
          {isRtl ? <ArrowLeft className="h-4 w-4" aria-hidden="true" /> : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
        </Link>
      </div>
    </section>
  )
}

export default PricingSection
