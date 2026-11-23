import { useMemo } from "react"
import { useW92Copy } from "@/i18n/w9_2Product"
import { EMPTY_LOADED_FILTERS, countLoadedFilters, loadedFilterOptions } from "./loadedFilters"

/**
 * W9-2 (D3): controls for filtering the Discover results already loaded.
 * Changing them only re-filters in memory; it never calls the API.
 * @param {{items: object[], filters: typeof EMPTY_LOADED_FILTERS, onChange: (f: typeof EMPTY_LOADED_FILTERS) => void, shown: number}} props
 */
export function LoadedResultsFilters({ items, filters, onChange, shown }) {
  const w = useW92Copy()
  const options = useMemo(() => loadedFilterOptions(items), [items])
  const set = (key, value) => onChange({ ...filters, [key]: value })
  const selectClass = "rounded border border-border bg-surface-2 px-1.5 py-0.5 text-xs text-text"

  function select(key, label, values, renderLabel = (v) => v) {
    return (
      <label className="flex items-center gap-1">
        <span className="text-text-faint">{label}</span>
        <select className={selectClass} value={filters[key]} onChange={(e) => set(key, e.target.value)} dir="auto">
          <option value="">{w.anyOption}</option>
          {values.map((v) => <option key={v} value={v}>{renderLabel(v)}</option>)}
        </select>
      </label>
    )
  }

  return (
    <div role="group" aria-label={w.loadedFiltersLabel} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border bg-surface px-3 py-1.5 text-xs" data-testid="loaded-filters">
      {select("format", w.mediaType, options.formats)}
      {select("status", w.status, options.statuses, (v) => (v === "stopped" ? w.statusStopped : w.statusActive))}
      {options.ctas.length ? select("cta", w.cta, options.ctas) : null}
      {options.domains.length ? select("domain", w.landingDomain, options.domains) : null}
      {options.maxDays > 1 ? (
        <label className="flex items-center gap-1">
          <span className="text-text-faint">{w.minRunLength(filters.minDays)}</span>
          <input
            type="range"
            min={0}
            max={options.maxDays}
            step={1}
            value={Math.min(filters.minDays, options.maxDays)}
            onChange={(e) => set("minDays", Number(e.target.value))}
            aria-label={w.minRunLength(filters.minDays)}
          />
        </label>
      ) : null}
      <span className="text-text-faint" role="status">{w.showingLoaded(shown, items.length)}</span>
      {countLoadedFilters(filters) ? (
        <button type="button" className="text-accent hover:underline" onClick={() => onChange(EMPTY_LOADED_FILTERS)}>
          {w.clearLoadedFilters}
        </button>
      ) : null}
      <span className="w-full text-[11px] text-text-faint">{w.loadedFiltersHint}</span>
    </div>
  )
}
