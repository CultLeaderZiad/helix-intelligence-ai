import React from "react"
import { NavLink, useLocation } from "react-router-dom"
import { Users, Crosshair, MapPin } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Scout parent sub-nav — honest tabs across the three Scout surfaces.
 * Sidebar keeps a single Scout entry; this lives INSIDE Scout.
 *   /scout/social          → Social / Atlas   (helix_scout + ScrapeGraph + atlas)
 *   /scout/lead-generation → Lead Generation   (scrapling_engine)
 *   /scout/maps            → Maps             (existing maps scout)
 */
const TABS = [
  { to: "/scout/social", label: "Social / Atlas", icon: Users },
  { to: "/scout/lead-generation", label: "Lead Generation", icon: Crosshair },
  { to: "/scout/maps", label: "Maps", icon: MapPin },
]

export function ScoutLeadGenSubNav({ right = null, className = "" }) {
  const { pathname } = useLocation()
  return (
    <div className={cn("sticky top-11 md:top-0 z-20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border bg-[#101015]/95 backdrop-blur-md px-3 sm:px-6 py-2 font-mono text-xs", className)}>
      <nav aria-label="Scout sections" className="flex items-center gap-1.5 bg-[#09090b] p-1 rounded border border-border overflow-x-auto max-w-full">
        {TABS.map(({ to, label, icon: Icon }) => {
          const active = pathname === to
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                "flex items-center gap-2 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all",
                active
                  ? "bg-accent text-black font-bold shadow-sm shadow-accent/20"
                  : "text-text-muted hover:text-white"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </NavLink>
          )
        })}
      </nav>
      {right}
    </div>
  )
}

export default ScoutLeadGenSubNav
