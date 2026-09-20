import React from "react"
import { Users, MapPin, CheckCircle2, ShieldCheck, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

export function ScoutModeTabs({
  mode = "social",
  onSelectMode,
  settings,
  credits = 0,
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border bg-[#101015] px-4 sm:px-6 py-2.5 font-mono text-xs">
      {/* Dual Mode Switcher */}
      <div className="flex items-center gap-1.5 bg-[#09090b] p-1 rounded border border-border">
        <button
          type="button"
          onClick={() => onSelectMode("social")}
          className={cn(
            "flex items-center gap-2 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all",
            mode === "social"
              ? "bg-accent text-black font-bold shadow-sm shadow-accent/20"
              : "text-text-muted hover:text-white"
          )}
        >
          <Users className="h-3.5 w-3.5" />
          <span>Social profiles</span>
        </button>

        <button
          type="button"
          onClick={() => onSelectMode("maps")}
          className={cn(
            "flex items-center gap-2 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all",
            mode === "maps"
              ? "bg-accent text-black font-bold shadow-sm shadow-accent/20"
              : "text-text-muted hover:text-white"
          )}
        >
          <MapPin className="h-3.5 w-3.5" />
          <span>Maps leads</span>
        </button>
      </div>

      {/* Live Status Strip */}
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-text-muted">
        {/* Scout Live Badge */}
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
          </span>
          <span className="font-bold text-white uppercase tracking-wider">SCOUT LIVE</span>
        </div>

        <span className="text-text-faint">|</span>

        {/* Credits */}
        <div className="flex items-center gap-1">
          <Zap className="h-3 w-3 text-accent" />
          <span className="text-white font-bold">{credits?.toFixed ? credits.toFixed(1) : credits}</span>
          <span className="text-text-faint">credits</span>
        </div>

        <span className="text-text-faint hidden md:inline">|</span>

        {/* LinkedIn BYOK status */}
        <div className="hidden md:flex items-center gap-1">
          <span>LinkedIn:</span>
          <span className={settings?.linkedin_configured ? "text-accent font-bold" : "text-text-faint"}>
            {settings?.linkedin_configured ? "BYOK active" : "not configured"}
          </span>
        </div>

        <span className="text-text-faint hidden md:inline">|</span>

        {/* Hunter status */}
        <div className="hidden md:flex items-center gap-1">
          <span>Hunter.io:</span>
          <span className={settings?.hunter_configured ? "text-accent font-bold" : "text-text-faint"}>
            {settings?.hunter_configured ? "active" : "off"}
          </span>
        </div>
      </div>
    </div>
  )
}

export default ScoutModeTabs
