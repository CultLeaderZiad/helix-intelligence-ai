import { ArrowRight, Search, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"

export function Hero() {
  const { t } = useLanguage()

  return (
    <section className="relative overflow-hidden border-b border-white/[0.08] bg-[#07070a] text-white">
      <div className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-20 sm:px-8 sm:py-28 lg:grid-cols-[1.1fr_0.9fr] lg:px-12">
        <div className="max-w-3xl">
          <p className="mb-5 inline-flex rounded border border-accent/25 bg-accent/5 px-3 py-1.5 font-mono text-xs text-accent">
            {t("marketingHeroLabel")}
          </p>
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            {t("marketingHeroTitle")}
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-text-muted sm:text-lg">
            {t("marketingHeroBody")}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              to="/sign-in"
              className="inline-flex items-center gap-2 rounded bg-accent px-5 py-3 text-sm font-semibold text-black transition hover:brightness-110"
            >
              {t("marketingSignIn")}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <a
              href="#product-capabilities"
              className="text-sm font-medium text-text-muted underline decoration-white/25 underline-offset-4 hover:text-white"
            >
              {t("marketingCapabilities")}
            </a>
          </div>
          <p className="mt-6 text-sm text-text-muted">{t("marketingAdminAccess")}</p>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-text-faint">
            {t("marketingHeroCaveat")}
          </p>
        </div>

        <div className="mx-auto w-full max-w-md rounded-xl border border-white/10 bg-white/[0.03] p-5 shadow-2xl shadow-black/30">
          <div className="flex items-center gap-3 border-b border-white/10 pb-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <Search className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <p className="font-semibold text-white">Helix Intelligence</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-text-faint">
                {t("marketingCapabilities")}
              </p>
            </div>
          </div>
          <div className="grid gap-3 pt-4 sm:grid-cols-2">
            <div className="rounded-lg border border-white/[0.08] bg-black/20 p-4">
              <Search className="mb-3 h-4 w-4 text-accent" aria-hidden="true" />
              <p className="text-sm font-medium text-white">{t("marketingDiscoverTitle")}</p>
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-black/20 p-4">
              <Sparkles className="mb-3 h-4 w-4 text-accent" aria-hidden="true" />
              <p className="text-sm font-medium text-white">{t("marketingCreativeTitle")}</p>
            </div>
          </div>
          <p className="mt-4 text-xs leading-5 text-text-faint">{t("marketingCapabilitiesIntro")}</p>
        </div>
      </div>
    </section>
  )
}

export default Hero
