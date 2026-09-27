import React from "react"
import { BookMarked, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * RecipeLibrary — GET /recipes (JSON files under app/data/leadgen_recipes).
 * Selecting a recipe adopts its mode/engine defaults into the job form.
 */
export function RecipeLibrary({ recipes, selectedId, onSelect, onAdopt, disabled }) {
  if (!recipes || recipes.length === 0) {
    return (
      <div className="rounded border border-border bg-surface/50 px-3 py-2.5 font-mono text-[11px] text-text-muted">
        No recipes loaded — jobs still run with your manual engine + selector defaults.
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <span className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-text-faint font-semibold">
        <BookMarked className="h-3.5 w-3.5" /> recipe library
      </span>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {recipes.map((r) => {
          const active = r.id === selectedId
          return (
            <button
              key={r.id}
              type="button"
              disabled={disabled}
              onClick={() => {
                onSelect(active ? null : r.id)
                if (!active) onAdopt?.(r)
              }}
              className={cn(
                "text-left rounded border px-3 py-2 font-mono transition-all",
                active
                  ? "border-accent bg-accent/10"
                  : "border-border bg-surface/60 hover:border-border/80 hover:bg-surface",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className={cn("text-xs font-semibold", active ? "text-accent" : "text-white")}>
                  {r.label}
                </span>
                {active && <CheckCircle2 className="h-3.5 w-3.5 text-accent shrink-0" />}
              </div>
              <div className="mt-0.5 text-[10px] text-text-faint uppercase tracking-wider">
                {r.mode} · {r.engine_default} · max {r.max_pages}p {r.adaptive ? "· adaptive" : ""}
              </div>
              <div className="mt-1 text-[11px] text-text-muted leading-snug line-clamp-2">
                {r.description}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default RecipeLibrary
