import { useEffect, useState, useRef } from "react"
import { useLocation } from "react-router-dom"
import { Menu, X, Search } from "lucide-react"
import { Sidebar } from "./Sidebar"
import { StatusBar } from "./StatusBar"
import { CommandBar } from "./CommandBar"
import { Button } from "@/components/ui/Button"
import { TrialBanner } from "@/components/ui/TrialBanner"
import { UpdatesBanner } from "@/components/UpdatesBanner"
import { ScrollToTopButton } from "@/components/ui/ScrollToTopButton"
import { FloatingSupportButton } from "@/components/ui/FloatingSupportButton"
import { SkipToContent } from "@/components/ui/SkipToContent"

/**
 * Workstation chrome: fixed rail, scrollable workspace, instrument strip.
 * The rail collapses to an overlay below `md` so the dense tables get the
 * full viewport width on small screens.
 */
export function AppShell({ children }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  const mainRef = useRef(null)

  // Global command shortcut (⌘K / Ctrl+K)
  useEffect(() => {
    function onKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setCommandOpen((v) => !v)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  // Auto-close mobile drawer on route change
  useEffect(() => {
    setNavOpen(false)
  }, [location.pathname])

  // Close mobile drawer on Escape key
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape" && navOpen) {
        setNavOpen(false)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [navOpen])

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-bg">
      {/* Skip to Content for keyboard accessibility */}
      <SkipToContent targetId="main-content" />

      <div className="flex min-h-0 flex-1">
        <Sidebar
          className="hidden md:flex"
          onOpenCommand={() => setCommandOpen(true)}
        />

        {/* Mobile Navigation Drawer with Backdrop Blur and Escape Handling */}
        {navOpen ? (
          <div className="fixed inset-0 z-50 flex md:hidden" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
            <div
              className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity duration-200"
              onClick={() => setNavOpen(false)}
              aria-hidden="true"
            />
            <div className="relative flex flex-col z-10 w-[240px] max-w-[85vw] h-full shadow-2xl bg-surface border-r border-border animate-in slide-in-from-left duration-200">
              <div className="flex h-11 shrink-0 items-center justify-between border-b border-border px-3 bg-surface-2">
                <div className="flex items-center gap-2">
                  <img
                    src="/brand/helix-mark.svg"
                    alt="Helix"
                    className="h-4 w-4 shrink-0 rounded-[3px] object-contain"
                  />
                  <span className="font-mono text-xs font-bold text-text">Helix Navigation</span>
                </div>
                <button
                  type="button"
                  onClick={() => setNavOpen(false)}
                  className="rounded p-1 text-text-muted hover:text-text hover:bg-surface-3 transition-colors cursor-pointer"
                  aria-label="Close navigation"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div
                className="flex-1 overflow-y-auto"
                onClick={(e) => {
                  if (e.target.closest('a')) setNavOpen(false)
                }}
              >
                <Sidebar
                  onOpenCommand={() => {
                    setCommandOpen(true)
                    setNavOpen(false)
                  }}
                  className="w-full border-r-0"
                />
              </div>
            </div>
          </div>
        ) : null}

        <main id="main-content" tabIndex={-1} ref={mainRef} className="flex min-w-0 flex-1 flex-col overflow-y-auto focus:outline-none">
          {/* Mobile Sticky Top Header — stays anchored while scrolling */}
          <div className="sticky top-0 z-30 flex h-11 shrink-0 items-center justify-between border-b border-border bg-surface/95 backdrop-blur-md px-2.5 md:hidden">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setNavOpen(true)}
                aria-label="Open navigation"
                className="h-8 w-8 text-text-muted hover:text-text"
              >
                {navOpen ? (
                  <X className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Menu className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
              <div className="flex items-center gap-1.5 font-mono text-[13px] font-bold text-text">
                <img src="/brand/helix-mark.svg" alt="Helix" className="h-4 w-4 object-contain" />
                <span>Helix</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCommandOpen(true)}
                className="flex items-center gap-1 px-2 py-1 rounded bg-surface-2 border border-border text-[11px] font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
                aria-label="Open search command palette"
              >
                <Search className="h-3 w-3 text-text-faint" />
                <span>Search</span>
              </button>
            </div>
          </div>

          <UpdatesBanner />
          <TrialBanner />

          {children}
        </main>
      </div>

      <StatusBar />
      <CommandBar open={commandOpen} onClose={() => setCommandOpen(false)} />

      {/* Floating Persistent Support Access */}
      <FloatingSupportButton />

      {/* Floating Scroll to Top for in-app scroll container */}
      <ScrollToTopButton containerRef={mainRef} />
    </div>
  )
}
