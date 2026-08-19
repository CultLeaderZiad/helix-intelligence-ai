import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Logo } from "@/components/ui/Logo"
import { Button } from "@/components/ui/Button"

/**
 * ============================================================
 * PUBLIC HEADER — marketing + auth surfaces ONLY
 * ============================================================
 * This is the top nav for pre-authentication pages. It is deliberately
 * NOT used inside the app: the authenticated shell has the Sidebar rail,
 * BreadcrumbBar and StatusBar, and duplicating navigation there would be
 * two competing nav systems on one screen.
 *
 * Everything traces to existing tokens: rectangular (no pills), mono
 * wordmark, the lime primary Button for the single primary action, the
 * `--border` hairline on scroll. No blur, no glass, no new colour.
 * ============================================================
 */

/* Marketing destinations do not exist yet — these are honest anchors, not
   routes faked into the router. They become real links when the pages do. */
const NAV_LINKS = [
  { label: "Product", href: "#product" },
  { label: "Pricing", href: "#pricing" },
  { label: "Docs", href: "#docs" },
]

export function PublicHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  /* On scroll the header gains a hairline bottom border and a more opaque
     surface — a state change, not a blur effect. */
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  /* A quick fade for the mobile panel — no slide, no bounce. Lock the
     body scroll while it is open. */
  useEffect(() => {
    if (!menuOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prev
    }
  }, [menuOpen])

  return (
    <header
      className={cn(
        "sticky top-0 z-30 transition-colors duration-200",
        scrolled
          ? "border-b border-border bg-surface/95"
          : "border-b border-transparent bg-bg",
      )}
    >
      <div className="mx-auto flex h-12 w-full max-w-6xl items-center gap-4 px-4 md:px-6">
        <Link
          to="/"
          className="flex shrink-0 items-center rounded-sm focus-visible:outline-none"
          aria-label="Helix — home"
        >
          <Logo />
        </Link>

        {/* Desktop nav */}
        <nav
          className="ml-4 hidden items-center gap-1 md:flex"
          aria-label="Primary"
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="rounded-sm px-2.5 py-1.5 text-[13px] text-text-muted transition-colors hover:bg-surface-2 hover:text-text"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <Button as={Link} to="/sign-in" variant="ghost" size="sm">
            Sign in
          </Button>
          <Button as={Link} to="/sign-up" variant="primary" size="sm">
            Get started
          </Button>
        </div>

        {/* Mobile trigger */}
        <div className="ml-auto flex items-center md:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <X className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Menu className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {/* Mobile panel — full-height, same links stacked, quick fade only. */}
      {menuOpen ? (
        <div className="animate-fade fixed inset-0 top-12 z-30 flex flex-col bg-bg md:hidden">
          <nav
            className="flex flex-col gap-0.5 border-t border-border p-3"
            aria-label="Primary"
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-sm px-2 py-2.5 text-sm text-text-muted transition-colors hover:bg-surface-2 hover:text-text"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mt-auto flex flex-col gap-2 border-t border-border p-3">
            <Button
              as={Link}
              to="/sign-in"
              variant="outline"
              size="lg"
              className="w-full"
              onClick={() => setMenuOpen(false)}
            >
              Sign in
            </Button>
            <Button
              as={Link}
              to="/sign-up"
              variant="primary"
              size="lg"
              className="w-full"
              onClick={() => setMenuOpen(false)}
            >
              Get started
            </Button>
          </div>
        </div>
      ) : null}
    </header>
  )
}
