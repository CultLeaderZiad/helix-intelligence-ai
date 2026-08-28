import { Checkbox, Label, Select } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { PLATFORMS, FORMATS, SPEND_BANDS, COUNTRIES } from "@/lib/constants"
import { cn } from "@/lib/utils"

const SCORE_OPTIONS = [
  { value: "0", label: "Any score" },
  { value: "6", label: "6.0 and above" },
  { value: "7", label: "7.0 and above" },
  { value: "8", label: "8.0 and above" },
  { value: "9", label: "9.0 and above" },
]

const DAYS_OPTIONS = [
  { value: "0", label: "Any duration" },
  { value: "14", label: "Running 14d+" },
  { value: "30", label: "Running 30d+" },
  { value: "60", label: "Running 60d+" },
  { value: "90", label: "Running 90d+" },
]

/**
 * Filter rail. Purely controlled — it holds no state of its own and does
 * not know that a service exists. Changes are staged locally in the page
 * and only applied when discovery is re-run, so the rail never triggers
 * a surprise job.
 */
export function FilterRail({ filters, onChange, onClear, dirty }) {
  function toggleArray(key, value) {
    const current = filters[key] ?? []
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value]
    onChange({ ...filters, [key]: next })
  }

  const activeCount =
    (filters.platforms?.length ?? 0) +
    (filters.formats?.length ?? 0) +
    (filters.spend_bands?.length ?? 0) +
    (filters.min_score > 0 ? 1 : 0) +
    (filters.min_days_active > 0 ? 1 : 0)

  return (
    <aside
      className="flex w-[196px] shrink-0 flex-col overflow-y-auto border-r border-border bg-surface"
      aria-label="Result filters"
    >
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-border px-3">
        <span className="label-mono">Filters</span>
        {activeCount > 0 ? (
          <button
            type="button"
            onClick={onClear}
            className="font-mono text-[10px] uppercase tracking-[0.06em] text-text-faint transition-colors hover:text-text"
          >
            clear
          </button>
        ) : null}
      </div>

      {/* One vertical rhythm for the whole rail: groups sit on a gap-5
          spine, every group is Label + gap-1.5 + controls. */}
      <div className="flex flex-col gap-5 p-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-country">Country</Label>
          <Select
            id="filter-country"
            value={filters.country ?? "ALL"}
            onChange={(e) => onChange({ ...filters, country: e.target.value })}
            options={COUNTRIES}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Platform</Label>
          {/* Checkbox carries its own py-1, so the list itself is gap-0 —
              otherwise rows sit 14px apart while Select groups sit at 6px. */}
          <div className="flex flex-col">
            {PLATFORMS.map((p) => (
              <Checkbox
                key={p.value}
                label={p.label}
                checked={(filters.platforms ?? []).includes(p.value)}
                onChange={() => toggleArray("platforms", p.value)}
              />
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Format</Label>
          <div className="flex flex-col">
            {FORMATS.map((f) => (
              <Checkbox
                key={f.value}
                label={f.label}
                checked={(filters.formats ?? []).includes(f.value)}
                onChange={() => toggleArray("formats", f.value)}
              />
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Spend band</Label>
          <div className="flex gap-1">
            {SPEND_BANDS.map((b) => {
              const active = (filters.spend_bands ?? []).includes(b.value)
              return (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => toggleArray("spend_bands", b.value)}
                  aria-pressed={active}
                  className={cn(
                    "tnum h-6 flex-1 rounded-sm border font-mono text-[11px] transition-colors",
                    active
                      ? // Selection reads through the accent hairline + wash.
                        // The glyph itself stays full-weight text so a
                        // selected band is not three accent signals at once.
                        "border-accent bg-accent-wash text-text"
                      : "border-border bg-surface-2 text-text-muted hover:border-border-strong hover:text-text",
                  )}
                >
                  {b.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-score">Composite score</Label>
          <Select
            id="filter-score"
            value={String(filters.min_score ?? 0)}
            onChange={(e) => onChange({ ...filters, min_score: Number(e.target.value) })}
            options={SCORE_OPTIONS}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-days">Longevity</Label>
          <Select
            id="filter-days"
            value={String(filters.min_days_active ?? 0)}
            onChange={(e) =>
              onChange({ ...filters, min_days_active: Number(e.target.value) })
            }
            options={DAYS_OPTIONS}
          />
        </div>

        {/* Staged-not-applied is a real state, so it is stated as one:
            a labelled 1px block, not a coloured accent stripe. */}
        {dirty ? (
          <div className="flex flex-col gap-1.5 border border-border bg-surface-2 p-2">
            <span className="label-mono text-warning">not applied</span>
            <p className="text-[11px] leading-relaxed text-text-muted">
              Filters changed since the last run. Re-run discovery to apply them.
            </p>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
