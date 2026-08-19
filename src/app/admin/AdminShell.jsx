import { useState } from "react"
import { Menu } from "lucide-react"
import { AdminSidebar } from "./AdminSidebar"
import { StatusBar } from "@/app/StatusBar"
import { Button } from "@/components/ui/Button"

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

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-bg">
      <div className="flex min-h-0 flex-1">
        <AdminSidebar className="hidden md:flex" />

        {navOpen ? (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-[#000]/70"
              onClick={() => setNavOpen(false)}
              aria-label="Close navigation"
            />
            <div className="relative flex" onClick={() => setNavOpen(false)}>
              <AdminSidebar />
            </div>
          </div>
        ) : null}

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border bg-surface px-2 md:hidden">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" aria-hidden="true" />
            </Button>
            <span className="text-[13px] font-medium text-text">Helix Console</span>
          </div>

          {children}
        </main>
      </div>

      <StatusBar />
    </div>
  )
}
