import { AlertTriangle, ArrowLeft, Database, Shield } from "lucide-react"
import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"

export function LegalPage() {
  const { t } = useLanguage()

  return (
    <div className="min-h-screen bg-[#07070a] font-sans text-text antialiased">
      <header className="sticky top-0 z-40 border-b border-border bg-[#07070a]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2 text-text-muted transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4 text-accent" aria-hidden="true" />
            <span className="text-sm">{t("legalBackHome")}</span>
          </Link>
          <span className="font-mono text-xs text-text-muted">{t("legalDraftLabel")}</span>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-10 px-4 py-12 sm:px-6 lg:px-8">
        <section className="space-y-4 border-b border-border pb-8">
          <div className="inline-flex items-center gap-2 rounded border border-accent/20 bg-accent/5 px-3 py-1.5 font-mono text-xs text-accent">
            <Shield className="h-4 w-4" aria-hidden="true" />
            {t("legalDraftLabel")}
          </div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t("legalTitle")}</h1>
          <p className="max-w-3xl text-sm leading-6 text-text-muted">{t("legalDescription")}</p>
          <div className="flex gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm leading-6 text-amber-100">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" aria-hidden="true" />
            <p>{t("legalDraftNotice")}</p>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">{t("legalServiceHeading")}</h2>
          <p className="text-sm leading-6 text-text-muted">{t("legalServiceBody")}</p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-accent" aria-hidden="true" />
            <h2 className="text-xl font-semibold">{t("legalDataHeading")}</h2>
          </div>
          <p className="text-sm leading-6 text-text-muted">{t("legalDataBody")}</p>
          <p className="text-sm leading-6 text-text-muted">{t("legalStorageDetail")}</p>
          <p className="text-sm leading-6 text-text-faint">{t("legalProviderCaveat")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">{t("legalSessionHeading")}</h2>
          <p className="text-sm leading-6 text-text-muted">{t("legalSessionBody")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">{t("legalContactHeading")}</h2>
          <p className="text-sm leading-6 text-text-muted">{t("legalContactBody")}</p>
        </section>
      </main>

      <MarketingFooter />
    </div>
  )
}

export default LegalPage
