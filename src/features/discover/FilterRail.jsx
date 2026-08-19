import { Checkbox, Label, Select } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { PLATFORMS, FORMATS, SPEND_BANDS } from "@/lib/constants"

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

      <div className="flex flex-col gap-4 p-3">
        <div className="flex flex-col gap-1">
          <Label>Platform</Label>
          {PLATFORMS.map((p) => (
            <Checkbox
              key={p.value}
              label={p.label}
              checked={(filters.platforms ?? []).includes(p.value)}
              onChange={() => toggleArray("platforms", p.value)}
            />
          ))}
        </div>

        <div className="flex flex-col gap-1">
          <Label>Format</Label>
          {FORMATS.map((f) => (
            <Checkbox
              key={f.value}
              label={f.label}
              checked={(filters.formats ?? []).includes(f.value)}
              onChange={() => toggleArray("formats", f.value)}
            />
          ))}
        </div>

        <div className="flex flex-col gap-1">
          <Label>Spend band</Label>
          <div className="flex gap-1 pt-0.5">
            {SPEND_BANDS.map((b) => {
              const active = (filters.spend_bands ?? []).includes(b.value)
              return (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => toggleArray("spend_bands", b.value)}
                  aria-pressed={active}
                  className={
                    active
                      ? "h-6 flex-1 rounded-sm border border-accent bg-accent-wash font-mono text-[11px] text-accent"
                      : "h-6 flex-1 rounded-sm border border-border bg-surface-2 font-mono text-[11px] text-text-muted transition-colors hover:border-border-strong hover:text-text"
                  }
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

        {dirty ? (
          <p className="border-l-2 border-warning/50 pl-2 text-[11px] leading-relaxed text-text-muted">
            Filters changed. Re-run discovery to apply them.
          </p>
        ) : null}
      </div>
    </aside>
  )
}
