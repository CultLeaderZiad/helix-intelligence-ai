import React from "react"
import { cn } from "@/lib/utils"

export const AVAILABLE_PLATFORMS = [
  { key: "instagram", label: "INSTAGRAM" },
  { key: "github", label: "GITHUB" },
  { key: "linktree", label: "LINKTREE" },
  { key: "tiktok", label: "TIKTOK" },
  { key: "youtube", label: "YOUTUBE" },
  { key: "twitch", label: "TWITCH" },
  { key: "pinterest", label: "PINTEREST" },
  { key: "linkedin", label: "LINKEDIN" },
]

export function PlatformPicker({ selectedPlatforms, onChange, disabled }) {
  const togglePlatform = (key) => {
    if (disabled) return
    if (selectedPlatforms.includes(key)) {
      if (selectedPlatforms.length > 1) {
        onChange(selectedPlatforms.filter((p) => p !== key))
      }
    } else {
      onChange([...selectedPlatforms, key])
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted font-semibold">
          PLATFORMS
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        {AVAILABLE_PLATFORMS.map((platform) => {
          const isSelected = selectedPlatforms.includes(platform.key)
          return (
            <button
              key={platform.key}
              type="button"
              disabled={disabled}
              onClick={() => togglePlatform(platform.key)}
              className={cn(
                "rounded-[4px] border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider transition-all select-none",
                isSelected
                  ? "border-accent bg-surface text-accent shadow-sm shadow-accent/10"
                  : "border-border bg-surface text-text-faint hover:border-border-strong hover:text-text",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {platform.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
