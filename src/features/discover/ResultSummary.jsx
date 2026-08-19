import { useMemo } from "react"
import { formatDuration, formatInt } from "@/lib/format"
import { SORT_OPTIONS } from "@/lib/constants"

/**
 * Result-set readout. A completed query is a research artefact, so its
 * parameters are stated in full: query, corpus size, recency, filters,
 * sort, selection. Every value comes from the result payload or from
 * page state — nothing is estimated.
 */

const ACTIVE_WINDOW_MS = 7 * 24 * 60 * 60 * 1000

function Cell({ label, children }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="label-mono">{label}</span>
      <span className="tnum font-mono text-[11px] text-text">{children}</span>
    </span>
  )
}

export function ResultSummary({ query, results, sort, filterCount, selectedId }) {
  const sortLabel =
    SORT_OPTIONS.find((o) => o.value === sort)?.label?.toLowerCase() ?? sort

  /* Recency is computed per page — the only rows actually in memory. */
  const activeOnPage = useMemo(() => {
    const cutoff = Date.now() - ACTIVE_WINDOW_MS
    return (results?.items ?? []).filter(
      (c) => c.last_seen && new Date(c.last_seen).getTime() >= cutoff,
    ).length
  }, [results?.items])

  if (!results) return null

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-1 border-b border-border bg-surface px-4 py-1.5">
      <span className="flex min-w-0 items-baseline gap-1.5">
        <span className="label-mono">query</span>
        <span className="truncate font-mono text-[11px] text-text">
          &quot;{query?.trim() || "*"}&quot;
        </span>
      </span>
      <Cell label="creatives">{formatInt(results.total)}</Cell>
      <Cell label="active ≤7d">
        {formatInt(activeOnPage)}
        <span className="text-text-faint">/page</span>
      </Cell>
      <Cell label="filters">{filterCount}</Cell>
      <Cell label="sort">{sortLabel}</Cell>
      {selectedId ? (
        <span className="flex items-baseline gap-1.5">
          <span className="label-mono text-accent">selected</span>
          <span className="font-mono text-[11px] text-text-muted">{selectedId}</span>
        </span>
      ) : null}
      <span className="tnum ml-auto font-mono text-[10px] text-text-faint">
        {formatDuration(results.took_ms)}
      </span>
    </div>
  )
}
