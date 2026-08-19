import { useState } from "react"
import { NavLink } from "react-router-dom"
import { ArrowLeft, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { Tag } from "@/components/ui/Tag"
import { ADMIN_NAV_GROUPS } from "./adminNavigation"

/**
 * Admin rail — structurally the twin of the customer Sidebar, but scoped
 * to operations and grouped. Group headers use the `// LABEL` monospace
 * treatment; items that have no implementation yet are still listed and
 * marked, never hidden and never dressed up as finished.
 *
 * The footer carries a route back into the customer app, because an
 * operator is also a user and the console is a mode, not a dead end.
 */
export function AdminSidebar({ className }) {
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
      aria-label="Admin"
    >
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <span
          className="h-2.5 w-2.5 shrink-0 bg-accent"
          aria-hidden="true"
          style={{ clipPath: "polygon(0 0, 100% 28%, 100% 100%, 0 72%)" }}
        />
        <span className="truncate text-[13px] font-medium tracking-tight text-text">
          Helix Console
        </span>
        <Tag tone="accent" className="ml-auto">
          Admin
        </Tag>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-2">
        {ADMIN_NAV_GROUPS.map((group) => (
          <div key={group.label} className="flex flex-col gap-0.5">
            <p className="label-mono px-1.5 pb-1 pt-1">{`// ${group.label}`}</p>
            {group.items.map((item) => (
              <NavLink
                key={item.key}
                to={item.path}
                end={item.end}
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
                    <item.icon
                      className={cn(
                        "h-3.5 w-3.5 shrink-0",
                        isActive ? "text-accent" : "text-text-faint",
                      )}
                      aria-hidden="true"
                    />
                    <span className="flex-1 truncate">{item.label}</span>
                    {!item.built ? (
                      <span
                        className="h-1 w-1 shrink-0 rounded-full bg-border-strong"
                        title="Not implemented yet"
                        aria-label="Not implemented yet"
                      />
                    ) : null}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t border-border p-2">
        <NavLink
          to="/discover"
          className="flex w-full items-center gap-2 rounded-sm border border-border bg-surface-2 px-1.5 py-[6px] text-xs text-text-muted transition-colors hover:border-border-strong hover:text-text"
        >
          <ArrowLeft className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="flex-1 truncate">Back to app</span>
        </NavLink>

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
      </div>
    </nav>
  )
}
