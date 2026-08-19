import { Search, SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Select } from "@/components/ui/Field"
import { KeyHint } from "@/components/ui/KeyHint"
import { SORT_OPTIONS } from "@/lib/constants"

/**
 * The query surface. Submitting enqueues a discovery job; changing sort
 * on an existing result set re-pages it without re-running the scrape.
 */
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
  function handleKeyDown(event) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return
    if (event.key === "Enter") {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2">
      <div className="relative flex h-8 min-w-0 flex-1 basis-[240px] items-center">
        <Search
          className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-text-faint"
          aria-hidden="true"
        />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Search ad copy, brand, domain — "quoted phrases" supported'
          aria-label="Discovery query"
          className="h-8 w-full rounded-sm border border-border bg-surface-2 pl-8 pr-3 text-[13px] text-text placeholder:text-text-faint transition-colors focus:border-border-strong focus:outline-none"
        />
      </div>

      <Button
        variant={filtersOpen ? "default" : "outline"}
        size="md"
        onClick={onToggleFilters}
        aria-expanded={filtersOpen}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
        Filters
        {activeFilterCount > 0 ? (
          <span className="tnum ml-0.5 font-mono text-[10px] text-accent">
            {activeFilterCount}
          </span>
        ) : null}
      </Button>

      <div className="w-[164px]">
        <Select
          value={sort}
          onChange={(e) => onSortChange(e.target.value)}
          options={SORT_OPTIONS}
          aria-label="Sort results"
          disabled={!canSort}
        />
      </div>

      <Button variant="primary" size="md" onClick={onSubmit} disabled={isBusy}>
        {isBusy ? "Running" : "Run discovery"}
        {!isBusy ? <KeyHint className="border-[#0A0A0A]/25 bg-[#0A0A0A]/10 text-[#0A0A0A]">↵</KeyHint> : null}
      </Button>
    </div>
  )
}
