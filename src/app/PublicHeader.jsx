import { useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"
import PillNav from "@/components/ui/PillNav"
import { LanguageSwitcher } from "@/components/LanguageSwitcher"
import { UpdatesBanner } from "@/components/UpdatesBanner"
import { useW8Copy } from "@/i18n/w8Product"
import { usePricingCopy } from "@/i18n/pricing"

export function PublicHeader() {
  const { isAuthenticated } = useAuth()
  const { t } = useLanguage()
  const c = useW8Copy()
  const pricing = usePricingCopy()
  const location = useLocation()
  const isHome = location.pathname === "/"
  const items = [
    { label: t("productNav"), href: isHome ? "#product" : "/#product" },
    // Pricing replaces the old Access link; the landing page keeps its Access section.
    { label: pricing.nav, href: "/pricing" },
    { label: c.navDocs, href: "/docs" },
    { label: t("updatesNavigation"), href: "/updates" },
    {
      label: t(isAuthenticated ? "consoleNav" : "signInNav"),
      href: isAuthenticated ? "/discover" : "/sign-in",
      isPrimary: true,
    },
  ]

  return (
    <>
      <UpdatesBanner />
      {/* Centered floating pill nav, as on the live landing page. The language
          switcher sits at the inline end on desktop and beside the menu on mobile. */}
      <header className="pointer-events-auto sticky top-0 z-50 flex w-full items-center justify-center px-4">
        <PillNav
          logo="/brand/helix-mark.svg"
          logoAlt="Helix"
          items={items}
          activeHref={location.pathname}
          ease="power2.out"
          baseColor="#0c0d0e"
          pillColor="#181a1b"
          hoverCircleColor="#ccff00"
          hoveredPillTextColor="#000000"
          pillTextColor="#ffffff"
          initialLoadAnimation
          ariaLabel={t("primaryNavigation")}
          homeLabel={t("homeLink")}
          menuOpenLabel={t("openMenu")}
          menuCloseLabel={t("closeMenu")}
        />
        <div className="shrink-0 md:absolute md:end-6 md:top-1/2 md:-translate-y-1/2">
          <LanguageSwitcher />
        </div>
      </header>
    </>
  )
}
