import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { LogOut, Bookmark, CreditCard, Users, Key, Shield, HelpCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { NAV_SECTIONS } from "./navigation"
import { KeyHint } from "@/components/ui/KeyHint"
import { NotificationBell } from "@/components/NotificationBell"

export function Sidebar({ onOpenCommand, className }) {
  const { user, signOut, updateUser } = useAuth()
  const [signingOut, setSigningOut] = useState(false)
  const navigate = useNavigate()

  function handleRestartTour() {
    updateUser({ has_completed_onboarding: false })
    navigate("/discover")
  }

  async function handleSignOut() {
    setSigningOut(true)
    try {
      await signOut()
    } finally {
      setSigningOut(false)
    }
  }

  const flags = user?.feature_flags || {}
  const showSwipeFiles = flags.swipe_files !== false
  const showTeam = flags.team_accounts === true
  const showApiKeys = flags.public_api === true

  return (
    <nav
      className={cn(
        "flex w-[196px] shrink-0 flex-col border-r border-border bg-surface",
        className,
      )}
      aria-label="Primary"
    >
      <div className="flex h-11 shrink-0 items-center justify-between border-b border-border px-3">
        <div className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 shrink-0 bg-accent"
            aria-hidden="true"
            style={{ clipPath: "polygon(0 0, 100% 28%, 100% 100%, 0 72%)" }}
          />
          <span className="truncate text-[13px] font-medium tracking-tight text-text">
            Helix Intelligence
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        <p className="label-mono px-1.5 pb-1.5 pt-1">Loops</p>
        {NAV_SECTIONS.map((section) => (
          <NavLink
            key={section.key}
            to={section.path}
            id={section.path === "/discover" ? "tour-discover-nav" : undefined}
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

        <p className="label-mono px-1.5 pb-1.5 pt-4">Workspace</p>

        {showSwipeFiles && (
          <NavLink
            to="/swipe-files"
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
                <Bookmark
                  className={cn(
                    "h-3.5 w-3.5 shrink-0",
                    isActive ? "text-accent" : "text-text-faint",
                  )}
                />
                <span className="flex-1 truncate">Swipe Files</span>
              </>
            )}
          </NavLink>
        )}

        <NavLink
          to="/billing"
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
              <CreditCard
                className={cn(
                  "h-3.5 w-3.5 shrink-0",
                  isActive ? "text-accent" : "text-text-faint",
                )}
              />
              <span className="flex-1 truncate">Billing & Meter</span>
            </>
          )}
        </NavLink>

        {showTeam && (
          <NavLink
            to="/team"
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
                <Users
                  className={cn(
                    "h-3.5 w-3.5 shrink-0",
                    isActive ? "text-accent" : "text-text-faint",
                  )}
                />
                <span className="flex-1 truncate">Team Members</span>
              </>
            )}
          </NavLink>
        )}

        {showApiKeys && (
          <NavLink
            to="/api-keys"
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
                <Key
                  className={cn(
                    "h-3.5 w-3.5 shrink-0",
                    isActive ? "text-accent" : "text-text-faint",
                  )}
                />
                <span className="flex-1 truncate">API Keys</span>
              </>
            )}
          </NavLink>
        )}

        {user?.role === "admin" && (
          <NavLink
            to="/admin/overview"
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-2 rounded-sm px-1.5 py-[7px] text-[13px] transition-colors mt-2 border-t border-border/50 pt-2",
                isActive
                  ? "bg-amber-500/10 text-amber-300"
                  : "text-amber-400/70 hover:bg-surface-2 hover:text-amber-300",
              )
            }
          >
            <Shield className="h-3.5 w-3.5 shrink-0 text-amber-400" />
            <span className="flex-1 truncate font-medium">Admin Center</span>
          </NavLink>
        )}
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t border-border p-2">
        <div className="flex items-center gap-2 px-1.5">
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs text-text">{user?.name || user?.email}</p>
            <div className="flex items-center gap-1.5">
              <span className="truncate font-mono text-[10px] uppercase tracking-[0.08em] text-text-faint">
                {user?.role}
              </span>
              {user?.credit_balance !== undefined && (
                <span className="text-[10px] font-mono text-amber-400 font-bold">
                  · {user.credit_balance.toFixed(1)}cr
                </span>
              )}
            </div>
          </div>

          <NotificationBell />

          <button
            type="button"
            onClick={handleRestartTour}
            className="rounded-sm p-1.5 text-text-faint transition-colors hover:bg-surface-2 hover:text-text"
            aria-label="Help & Tour"
            title="Help & Tour"
          >
            <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
          </button>

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
