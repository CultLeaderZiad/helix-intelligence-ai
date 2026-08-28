import { useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import PillNav from "@/components/ui/PillNav"

export function PublicHeader() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  const navItems = [
    { label: "Product", href: "#product" },
    { label: "Pricing", href: "#pricing" },
    { label: "Docs", href: "#docs" },
    ...(isAuthenticated
      ? [{ label: "Console", href: APP_HOME, isPrimary: true }]
      : [
          { label: "Sign in", href: "/sign-in" },
          { label: "Get started", href: "/sign-up", isPrimary: true }
        ]
    )
  ]

  return (
    <header className="sticky top-0 z-50 w-full flex justify-center px-4 pointer-events-auto">
      <PillNav
        logo="/helix-logo.svg"
        logoAlt="Helix"
        items={navItems}
        activeHref={location.pathname}
        className="custom-nav"
        ease="power2.easeOut"
        baseColor="#0c0d0e"
        pillColor="#181a1b"
        hoverCircleColor="#ccff00"
        hoveredPillTextColor="#000000"
        pillTextColor="#ffffff"
        initialLoadAnimation={true}
      />
    </header>
  )
}
