import { useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"
import PillNav from "@/components/ui/PillNav"
import { LanguageSwitcher } from "@/components/LanguageSwitcher"
import { UpdatesBanner } from "@/components/UpdatesBanner"

export function PublicHeader() {
  const { isAuthenticated } = useAuth()
  const { t } = useLanguage()
  const location = useLocation()
  const isHome = location.pathname === "/"
  const items = [
    { label: t("productNav"), href: isHome ? "#product" : "/#product" },
    { label: t("accessNav"), href: isHome ? "#pricing" : "/#pricing" },
    { label: t("docsNavigation"), href: "/docs" },
    { label: t("updatesNavigation"), href: "/updates" },
    { label: t(isAuthenticated ? "consoleNav" : "signInNav"), href: isAuthenticated ? "/discover" : "/sign-in", isPrimary: true },
  ]
  return (
    <>
      <UpdatesBanner />
      <header className="relative z-40 flex items-center justify-between gap-3 border-b border-border bg-bg px-4 py-3 sm:px-6">
        <PillNav logo="/brand/helix-mark.svg" logoAlt="Helix" items={items} activeHref={location.pathname} />
        <LanguageSwitcher />
      </header>
    </>
  )
}
