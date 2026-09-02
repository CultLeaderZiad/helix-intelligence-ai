import { Search, SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Select } from "@/components/ui/Field"
import { KeyHint } from "@/components/ui/KeyHint"
import { formatInt } from "@/lib/format"
import { useLanguage } from "@/context/LanguageContext"

export function SearchQueryBar({
  query,
  onQueryChange,
  sort,
  onSortChange,
  onSubmit,
  onToggleFilters,
  filtersOpen,
  activeFilterCount,
  isBusy,
  canSort,
}) {
  const { t, isRtl } = useLanguage()

  function handleKeyDown(event) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return
    if (event.key === "Enter") {
      event.preventDefault()
      onSubmit()
    }
  }

  const sortOptions = [
    { value: "composite_desc", label: t("sortComposite", "Composite score") },
    { value: "hook_desc", label: t("sortHook", "Hook score") },
    { value: "days_active_desc", label: t("sortDays", "Days active") },
    { value: "first_seen_desc", label: t("sortNewest", "Newest") },
    { value: "impressions_desc", label: t("sortImpr", "Est. impressions") },
  ]

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2">
      <div className="relative flex h-8 min-w-0 flex-1 basis-[240px] items-center">
        <Search
          className={`pointer-events-none absolute h-3.5 w-3.5 text-text-faint ${isRtl ? "right-2.5" : "left-2.5"}`}
          aria-hidden="true"
        />
        <input
          id="tour-search-input"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("searchPlaceholder", 'Search ad copy, brand, domain — "quoted phrases" supported')}
          aria-label="Discovery query"
          className={`h-8 w-full rounded-sm border border-border bg-surface-2 pr-3 text-[13px] text-text placeholder:text-text-faint transition-colors focus:border-border-strong focus:outline-none ${isRtl ? "pr-8 pl-3" : "pl-8 pr-3"}`}
        />
      </div>

      <Button
        variant={filtersOpen ? "default" : "outline"}
        size="md"
        onClick={onToggleFilters}
        aria-expanded={filtersOpen}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
        {t("filters", "Filters")}
        {activeFilterCount > 0 ? (
          <span className="tnum ml-0.5 font-mono text-[10px] text-text-muted">
            {formatInt(activeFilterCount)}
          </span>
        ) : null}
      </Button>

      <div className="w-[170px]">
        <Select
          value={sort}
          onChange={(e) => onSortChange(e.target.value)}
          options={sortOptions}
          aria-label="Sort results"
          disabled={!canSort}
        />
      </div>

      <Button variant="primary" size="md" onClick={onSubmit} disabled={isBusy || !query.trim()} className="font-bold">
        {isBusy ? t("running", "Running...") : t("runDiscovery", "Run discovery")}
        {!isBusy && query.trim() ? <KeyHint tone="on-accent">↵</KeyHint> : null}
      </Button>
    </div>
  )
}
