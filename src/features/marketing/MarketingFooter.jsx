import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"

export function MarketingFooter() {
  const { t } = useLanguage()

  return (
    <footer className="border-t border-white/[0.08] bg-[#050508] px-6 py-10 text-neutral-400 sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link to="/" className="text-lg font-semibold text-white">Helix Intelligence</Link>
          <p className="mt-2 max-w-md text-sm leading-6 text-text-muted">{t("footerDescription")}</p>
        </div>
        <div className="flex flex-col gap-3 text-sm sm:items-end">
          <Link to="/legal/subprocessors" className="text-accent underline underline-offset-4 hover:text-white">
            {t("legalTitle")}
          </Link>
          <p className="max-w-xl text-xs leading-5 text-text-faint sm:text-end">{t("footerLegalPending")}</p>
          <Link to="/sign-in" className="text-text-muted hover:text-white">{t("marketingSignIn")}</Link>
        </div>
      </div>
      <div className="mx-auto mt-8 flex max-w-7xl items-center justify-between border-t border-white/[0.08] pt-5 font-mono text-[10px] uppercase tracking-wider text-text-faint">
        <span>© 2026 HELIX</span>
        <span>{t("footerBeta")}</span>
      </div>
    </footer>
  )
}

export default MarketingFooter
