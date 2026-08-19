import { useState } from "react"
import { NavLink } from "react-router-dom"
import { LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { NAV_SECTIONS } from "./navigation"
import { KeyHint } from "@/components/ui/KeyHint"

/**
 * Fixed rail. Sections that have no backend yet are still listed but
 * marked — hiding them would misrepresent the shape of the product,
 * and styling them as finished would misrepresent its state.
 */
export function Sidebar({ onOpenCommand, className }) {
  const { user, signOut } = useAuth()
  const [signingOut, setSigningOut] = useState(false)

  async function handleSignOut() {
    setSigningOut(true)
    try {
      await signOut()
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <nav
      className={cn(
        "flex w-[188px] shrink-0 flex-col border-r border-border bg-surface",
        className,
      )}
      aria-label="Primary"
    >
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <span
          className="h-2.5 w-2.5 shrink-0 bg-accent"
          aria-hidden="true"
          style={{ clipPath: "polygon(0 0, 100% 28%, 100% 100%, 0 72%)" }}
        />
        <span className="truncate text-[13px] font-medium tracking-tight text-text">
          Helix Intelligence
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        <p className="label-mono px-1.5 pb-1.5 pt-1">Loops</p>
        {NAV_SECTIONS.map((section) => (
          <NavLink
            key={section.key}
            to={section.path}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-2 rounded-sm px-1.5 py-[7px] text-[13px] transition-colors",
                isActive
                  ? "bg-surface-3 text-text"
                  : "text-text-muted hover:bg-surface-2 hover:text-text",
              )
            }
          >
            {({ isActive }) => (
              <>
                <section.icon
                  className={cn(
                    "h-3.5 w-3.5 shrink-0",
                    isActive ? "text-accent" : "text-text-faint",
                  )}
                  aria-hidden="true"
                />
                <span className="flex-1 truncate">{section.label}</span>
                {section.status === "pending" ? (
                  <span
                    className="h-1 w-1 shrink-0 rounded-full bg-border-strong"
                    title="No data source connected"
                    aria-label="No data source connected"
                  />
                ) : null}
              </>
            )}
          </NavLink>
        ))}
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t border-border p-2">
        <div className="flex items-center gap-2 px-1.5">
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs text-text">{user?.name}</p>
            <p className="truncate font-mono text-[10px] uppercase tracking-[0.08em] text-text-faint">
              {user?.role}
            </p>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            disabled={signingOut}
            className="rounded-sm p-1.5 text-text-faint transition-colors hover:bg-surface-2 hover:text-text disabled:cursor-wait disabled:opacity-50"
            aria-label={signingOut ? "Signing out" : "Sign out"}
            title="Sign out"
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
        <button
          type="button"
          onClick={onOpenCommand}
          className="flex w-full items-center gap-2 rounded-sm border border-border bg-surface-2 px-1.5 py-[6px] text-left text-xs text-text-muted transition-colors hover:border-border-strong hover:text-text"
        >
          <span className="flex-1 truncate">Command</span>
          <KeyHint>⌘</KeyHint>
          <KeyHint>K</KeyHint>
        </button>
      </div>
    </nav>
  )
}
