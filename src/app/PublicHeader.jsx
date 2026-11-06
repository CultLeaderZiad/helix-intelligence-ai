import { Link, useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"
import PillNav from "@/components/ui/PillNav"
import { LanguageSwitcher } from "@/components/LanguageSwitcher"
import { UpdatesBanner } from "@/components/UpdatesBanner"

/**
 * React Router adapter for PillNav's `linkComponent` (which passes `href`).
 * In-page anchors (#product, /#access) stay plain links so the browser
 * scrolls to them; app routes use client-side navigation.
 * @param {{ href: string } & Record<string, any>} props
 */
function NavLink({ href, ...rest }) {
  if (href.includes("#") || /^[a-z]+:/i.test(href)) return <a href={href} {...rest} />
  return <Link to={href} {...rest} />
}

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
    { label: t(isAuthenticated ? "consoleNav" : "signInNav"), href: isAuthenticated ? "/discover" : "/sign-in" },
  ]
  // Highlight the item for the current route; on the landing page nothing is "current".
  const activeHref = items.some((item) => item.href === location.pathname) ? location.pathname : ""

  return (
    <>
      <UpdatesBanner />
      {/* Centered floating React Bits pill nav. The language switcher sits at the
          inline end on desktop and beside the folded menu on small screens. */}
      <header className="sticky top-0 z-50 flex w-full items-center gap-3 px-4 py-3 md:justify-center">
        {/* Full-width wrapper: PillNav folds into a menu by measuring this box. */}
        <div className="flex min-w-0 flex-1 justify-center md:px-40">
          <PillNav
            logo="/brand/helix-mark.svg"
            logoAlt={t("homeLink")}
            logoHref="/"
            items={items}
            activeHref={activeHref}
            linkComponent={NavLink}
            itemStyle="pill"
            hoverEffect="fill"
            indicator="dot"
            highlightColor="#d7ff4f"
            ariaLabel={t("primaryNavigation")}
            menuOpenLabel={t("openMenu")}
            menuCloseLabel={t("closeMenu")}
          />
        </div>
        <div className="shrink-0 md:absolute md:end-6 md:top-1/2 md:-translate-y-1/2">
          <LanguageSwitcher />
        </div>
      </header>
    </>
  )
}
