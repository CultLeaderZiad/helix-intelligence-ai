import { useState, useEffect } from "react"
import { useLocation } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { AdminSidebar } from "./AdminSidebar"
import { StatusBar } from "@/app/StatusBar"
import { Button } from "@/components/ui/Button"
import { UpdatesBanner } from "@/components/UpdatesBanner"

/**
 * Operations console chrome — the structural twin of AppShell, with its
 * own rail and no command bar (the console is navigated, not queried).
 * The instrument strip at the foot is shared, so the data-source and
 * live-state signal stay identical across both shells.
 *
 * The rail collapses to an overlay below `md` so the dense admin tables
 * get the full viewport width on small screens.
 */
export function AdminShell({ children }) {
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()

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
      <div className="flex min-h-0 flex-1">
        <AdminSidebar className="hidden md:flex" />

        {navOpen ? (
          <div className="fixed inset-0 z-50 flex md:hidden" role="dialog" aria-modal="true" aria-label="Console Navigation">
            <div
              className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity duration-200"
              onClick={() => setNavOpen(false)}
              aria-hidden="true"
            />
            <div className="relative flex flex-col z-10 w-[240px] max-w-[85vw] h-full shadow-2xl bg-surface border-r border-border animate-in slide-in-from-left duration-200">
              <div className="flex h-11 shrink-0 items-center justify-between border-b border-border px-3 bg-surface-2">
                <span className="font-mono text-xs font-bold text-text">Console Navigation</span>
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
                <AdminSidebar className="w-full border-r-0" />
              </div>
            </div>
          </div>
        ) : null}

        <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          {/* Sticky Mobile Header */}
          <div className="sticky top-0 z-30 flex h-11 shrink-0 items-center gap-2 border-b border-border bg-surface/95 backdrop-blur-md px-2.5 md:hidden">
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
            <span className="text-[13px] font-medium text-text">Helix Console</span>
          </div>

          <UpdatesBanner />

          {children}
        </main>
      </div>

      <StatusBar />
    </div>
  )
}
