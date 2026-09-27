import React from "react"
import { Gauge, Eye, MonitorCog, ShieldCheck, Cpu } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * EnginePicker — Scrapling capability map made honest control:
 *   http    → Fetcher         (fast TLS impersonation)
 *   stealth → StealthyFetcher (default; unknown / Cloudflare)
 *   dynamic → DynamicFetcher  (JS-heavy; Playwright)
 * Plus discover mode, robots_obey (default ON), adaptive relocate toggle.
 */
const ENGINES = [
  { id: "http", label: "http", hint: "fast TLS impersonation", icon: Gauge },
  { id: "stealth", label: "stealth", hint: "default · Cloudflare-ready", icon: Eye },
  { id: "dynamic", label: "dynamic", hint: "JS-heavy pages (Playwright)", icon: MonitorCog },
]

const MODES = [
  { id: "crawl", label: "Crawl" },
  { id: "sitemap", label: "Sitemap" },
  { id: "shopify", label: "Shopify" },
  { id: "csv_feed", label: "CSV / domain feed" },
  { id: "digest", label: "Markdown digest" },
]

export function EnginePicker({ value, onChange, mode, onModeChange, robotsObey, onRobotsChange, adaptive, onAdaptiveChange, disabled }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-faint font-semibold">engine</span>
        {ENGINES.map(({ id, label, hint, icon: Icon }) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            onClick={() => onChange(id)}
            title={hint}
            className={cn(
              "flex items-center gap-1.5 rounded border px-2.5 py-1 text-[11px] font-mono font-semibold uppercase tracking-wider transition-all",
              value === id
                ? "border-accent bg-accent/15 text-accent"
                : "border-border bg-surface text-text-muted hover:text-white hover:border-border/80",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-faint font-semibold">mode</span>
        {MODES.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            onClick={() => onModeChange(id)}
            className={cn(
              "rounded border px-2.5 py-1 text-[11px] font-mono font-semibold transition-all",
              mode === id
                ? "border-accent bg-accent/15 text-accent"
                : "border-border bg-surface text-text-muted hover:text-white",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-4 pt-1">
        <label className={cn("flex items-center gap-2 text-[11px] font-mono text-text-muted", disabled && "opacity-50")}>
          <input
            type="checkbox"
            checked={robotsObey}
            disabled={disabled}
            onChange={(e) => onRobotsChange(e.target.checked)}
            className="accent-accent"
          />
          <ShieldCheck className="h-3.5 w-3.5" />
          robots_txt_obey {robotsObey ? "on" : "— OFF (audited)"}
        </label>
        <label className={cn("flex items-center gap-2 text-[11px] font-mono text-text-muted", disabled && "opacity-50")}>
          <input
            type="checkbox"
            checked={adaptive}
            disabled={disabled}
            onChange={(e) => onAdaptiveChange(e.target.checked)}
            className="accent-accent"
          />
          <Cpu className="h-3.5 w-3.5" />
          adaptive relocate
        </label>
      </div>
      {!robotsObey && (
        <p className="text-[11px] font-mono text-warning">
          robots_obey=false will be written to the job audit log. Only use on sites whose ToS permits it.
        </p>
      )}
    </div>
  )
}

export default EnginePicker
