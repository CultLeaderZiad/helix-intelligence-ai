import { Label, Select } from "@/components/ui/Field"
import { COUNTRIES } from "@/lib/constants"
import { useW8Copy } from "@/i18n/w8Product"

/** Longevity presets the results endpoint accepts (0 = no preset). */
export const LONGEVITY_PRESETS = [0, 30, 60, 90]
const RUBRIC_MINIMUMS = [0, 6, 7, 8, 9]

/** How many result filters differ from the defaults. */
export function countActiveFilters(filters) {
  return (
    ((filters?.country ?? "ALL") !== "ALL" ? 1 : 0) +
    ((filters?.min_days_active ?? 0) > 0 ? 1 : 0) +
    ((filters?.min_score ?? 0) > 0 ? 1 : 0)
  )
}

/**
 * Filter rail. Purely controlled. Only controls that the backend really
 * applies are shown: country is sent with the search (staged until the
 * search is run again); run length and the text-rubric minimum filter the
 * stored results and apply instantly without spending credits.
 */
export function FilterRail({ filters, onChange, onClear, dirty }) {
  const c = useW8Copy()
  const longevityOptions = LONGEVITY_PRESETS.map((days) => ({
    value: String(days),
    label: days === 0 ? c.longevityAny : c[`longevity${days}`],
  }))
  const rubricOptions = RUBRIC_MINIMUMS.map((n) => ({
    value: String(n),
    label: n === 0 ? c.rubricAny : c.rubricMin(n),
  }))

  return (
    <aside
      className="flex w-[196px] shrink-0 flex-col overflow-y-auto border-e border-border bg-surface"
      aria-label={c.filters}
    >
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-border px-3">
        <span className="label-mono">{c.filters}</span>
        {countActiveFilters(filters) > 0 ? (
          <button
            type="button"
            onClick={onClear}
            className="font-mono text-[10px] uppercase tracking-[0.06em] text-text-faint transition-colors hover:text-text"
          >
            {c.clear}
          </button>
        ) : null}
      </div>

      <div className="flex flex-col gap-5 p-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-days">{c.longevity}</Label>
          <Select
            id="filter-days"
            value={String(filters.min_days_active ?? 0)}
            onChange={(e) => onChange({ ...filters, min_days_active: Number(e.target.value) })}
            options={longevityOptions}
          />
          <p className="text-[11px] leading-relaxed text-text-faint">{c.longevityHint}</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-score">{c.rubric}</Label>
          <Select
            id="filter-score"
            value={String(filters.min_score ?? 0)}
            onChange={(e) => onChange({ ...filters, min_score: Number(e.target.value) })}
            options={rubricOptions}
          />
          <p className="text-[11px] leading-relaxed text-text-faint">{c.rubricHint}</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-country">{c.country}</Label>
          <Select
            id="filter-country"
            value={filters.country ?? "ALL"}
            onChange={(e) => onChange({ ...filters, country: e.target.value })}
            options={COUNTRIES}
          />
          <p className="text-[11px] leading-relaxed text-text-faint">{c.countryHint}</p>
        </div>

        {dirty ? (
          <div className="flex flex-col gap-1.5 border border-border bg-surface-2 p-2">
            <span className="label-mono text-warning">{c.notApplied}</span>
            <p className="text-[11px] leading-relaxed text-text-muted">{c.notAppliedBody}</p>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
