import React from "react"
import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

const CATEGORY_PRESETS = [
  "Beauty & Aesthetics MENA",
  "B2B SaaS Founders",
  "Specialty Coffee & Roasteries",
  "Dermatology & Dental Clinics",
  "D2C Luxury & Fashion",
]

export function TargetCategoryField({
  value = "",
  onChange,
  disabled = false,
  className = "",
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between">
        <label className="block font-mono text-[10px] uppercase tracking-[0.14em] text-accent font-bold">
          TARGET CATEGORY / BUSINESS CONTEXT (ATLAS)
        </label>
        <span className="text-[10px] font-mono text-text-faint">
          Drives Atlas relevance score & personalized cold outreach
        </span>
      </div>

      <div className="relative">
        <input
          type="text"
          disabled={disabled}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder="e.g. MENA clinics, Aesthetics, B2B SaaS Founders, Specialty Coffee"
          className="w-full rounded-[4px] border border-border bg-[#09090b] px-3 py-2 font-mono text-[12px] text-text placeholder:text-text-faint focus:border-accent focus:outline-none transition-colors"
        />
      </div>

      {/* Quick Suggestion Chips */}
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className="text-[9.5px] font-mono uppercase text-text-faint tracking-wider mr-0.5">
          Suggestions:
        </span>
        {CATEGORY_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            disabled={disabled}
            onClick={() => onChange?.(preset)}
            className={cn(
              "rounded px-2 py-0.5 font-mono text-[10px] border transition-colors",
              value.toLowerCase() === preset.toLowerCase()
                ? "bg-accent/15 border-accent text-accent font-semibold"
                : "bg-surface-2 border-border/70 text-text-muted hover:text-white hover:border-border"
            )}
          >
            {preset}
          </button>
        ))}
      </div>
    </div>
  )
}
