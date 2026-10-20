import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"

export function MarketingFooter() {
  const { t } = useLanguage()
  return (
    <footer className="border-t border-border bg-bg px-6 py-10 text-text-muted">
      <div className="mx-auto max-w-7xl space-y-4 text-sm">
        <Link to="/" className="font-semibold text-text">Helix Intelligence</Link>
        <p className="max-w-3xl leading-relaxed">{t("footerDisclosure")}</p>
        <p className="max-w-3xl text-xs leading-relaxed">{t("footerDraft")}</p>
        <nav aria-label={t("footerLegal")} className="flex flex-wrap gap-5">
          <Link to="/legal" className="hover:text-text">{t("footerLegal")}</Link>
          <Link to="/docs" className="hover:text-text">{t("docsNavigation")}</Link>
          <Link to="/sign-in" className="hover:text-text">{t("signInNav")}</Link>
        </nav>
      </div>
    </footer>
  )
}

export default MarketingFooter
