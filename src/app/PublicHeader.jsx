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
    { label: t("accessNav"), href: isHome ? "#access" : "/#access" },
    { label: t("docsNavigation"), href: "/docs" },
    { label: t("updatesNavigation"), href: "/updates" },
    { label: t(isAuthenticated ? "consoleNav" : "signInNav"), href: isAuthenticated ? "/discover" : "/sign-in", isPrimary: true },
  ]
  return (
    <>
      <UpdatesBanner />
      {/* Centered floating pill nav, as on the live landing page. The language
          switcher sits at the inline end on desktop and beside the menu on mobile. */}
      <header className="sticky top-0 z-50 flex w-full items-center gap-3 px-4 md:justify-center">
        <div className="min-w-0 flex-1 md:flex md:flex-none md:justify-center">
          <PillNav logo="/brand/helix-mark.svg" logoAlt="Helix" items={items} activeHref={location.pathname} />
        </div>
        <div className="shrink-0 md:absolute md:end-6 md:top-1/2 md:-translate-y-1/2">
          <LanguageSwitcher />
        </div>
      </header>
    </>
  )
}
