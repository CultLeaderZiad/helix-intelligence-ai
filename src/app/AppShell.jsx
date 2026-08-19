import { useEffect, useState } from "react"
import { Menu, X } from "lucide-react"
import { Sidebar } from "./Sidebar"
import { StatusBar } from "./StatusBar"
import { CommandBar } from "./CommandBar"
import { Button } from "@/components/ui/Button"

/**
 * Workstation chrome: fixed rail, scrollable workspace, instrument strip.
 * The rail collapses to an overlay below `md` so the dense tables get the
 * full viewport width on small screens.
 */
export function AppShell({ children }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)

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

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-bg">
      <div className="flex min-h-0 flex-1">
        <Sidebar
          className="hidden md:flex"
          onOpenCommand={() => setCommandOpen(true)}
        />

        {navOpen ? (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-[#000]/70"
              onClick={() => setNavOpen(false)}
              aria-label="Close navigation"
            />
            <div className="relative flex" onClick={() => setNavOpen(false)}>
              <Sidebar onOpenCommand={() => setCommandOpen(true)} />
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
              {navOpen ? (
                <X className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Menu className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
            <span className="text-[13px] font-medium text-text">Helix Intelligence</span>
          </div>

          {children}
        </main>
      </div>

      <StatusBar />
      <CommandBar open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  )
}
