import { useEffect, useMemo, useState } from "react"
import { Radar, SearchX } from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { useTelemetry } from "@/app/TelemetryContext"
import { SearchQueryBar } from "@/features/discover/SearchQueryBar"
import { FilterRail } from "@/features/discover/FilterRail"
import { JobProgress } from "@/features/discover/JobProgress"
import { ResultSummary } from "@/features/discover/ResultSummary"
import { ResultsTable } from "@/features/discover/ResultsTable"
import { CreativeDetailPanel } from "@/features/discover/CreativeDetailPanel"
import { Button } from "@/components/ui/Button"
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States"
import { PHASE, useDiscoverySearch } from "@/hooks/useDiscoverySearch"
import { useIsBelowLg } from "@/hooks/useMediaQuery"
import { useAuth } from "@/context/AuthContext"
import { formatDuration, formatInt } from "@/lib/format"
import { OnboardingTour } from "@/app/OnboardingTour"

const EMPTY_FILTERS = {
  country: "ALL",
  platforms: [],
  formats: [],
  spend_bands: [],
  min_score: 0,
  min_days_active: 0,
}

/**
 * ============================================================
 * DISCOVER — the only page wired to a live loop
 * ============================================================
 * This page is the composition root for the discovery flow. It owns the
 * *query intent* (text, staged filters, sort, selection) and delegates
 * every async concern to `useDiscoverySearch`, which is the sole route to
 * the service layer. No child here touches a service or a fixture.
 *
 * Filters are staged, not live: editing the rail does not fire a job, so
 * a half-built filter set can never trigger a scrape. `dirty` tells the
 * rail to say so out loud.
 * ============================================================
 */
export function DiscoverPage() {
  const [query, setQuery] = useState("")
  const [sort, setSort] = useState("composite_desc")
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [selectedId, setSelectedId] = useState(null)

  const isBelowLg = useIsBelowLg()
  const { report } = useTelemetry()
  const { user, updateUser } = useAuth()
  const { phase, job, results, error, submit, refine, cancel, retry, isBusy } =
    useDiscoverySearch()

  const dirty = useMemo(
    () => JSON.stringify(draftFilters) !== JSON.stringify(appliedFilters),
    [draftFilters, appliedFilters],
  )

  const activeFilterCount = useMemo(
    () =>
      (draftFilters.platforms?.length ?? 0) +
      (draftFilters.formats?.length ?? 0) +
      (draftFilters.spend_bands?.length ?? 0) +
      (draftFilters.min_score > 0 ? 1 : 0) +
      (draftFilters.min_days_active > 0 ? 1 : 0),
    [draftFilters],
  )

  /* Publish measured values into the shell's instrument strip. */
  useEffect(() => {
    if (phase === PHASE.SUBMITTING || phase === PHASE.RUNNING) {
      report({
        state: "running",
        lastJobId: job?.job_id ?? null,
        records: job?.records_found ?? null,
      })
    } else if (phase === PHASE.READY && results) {
      report({
        state: "ready",
        records: results.total,
        tookMs: results.took_ms ?? null,
        countRequest: true,
      })
    } else if (phase === PHASE.ERROR) {
      report({ state: "error" })
    }
  }, [phase, job?.job_id, job?.records_found, results, report])

  function runDiscovery() {
    if (!query.trim()) return
    setSelectedId(null)
    setAppliedFilters(draftFilters)
    submit({ query: query.trim(), filters: draftFilters, sort })
  }

  function handleSortChange(next) {
    setSort(next)
    if (phase === PHASE.READY) refine({ page: 1, sort: next })
  }

  function clearFilters() {
    setDraftFilters(EMPTY_FILTERS)
  }

  const items = results?.items ?? []
  const showProgress = Boolean(job) && phase !== PHASE.READY && phase !== PHASE.IDLE
  const inspectorOpen = Boolean(selectedId)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <OnboardingTour user={user} onComplete={() => updateUser({ has_completed_onboarding: true })} />
      <BreadcrumbBar
        trail={["Helix", "Discover"]}
        meta={
          phase === PHASE.READY && results
            ? `${formatInt(results.total)} ${results.total === 1 ? "record" : "records"} · ${formatDuration(results.took_ms)}`
            : "no result set"
        }
        actions={
          phase === PHASE.READY ? (
            <Button size="xs" variant="ghost" onClick={cancel}>
              Clear set
            </Button>
          ) : null
        }
      />

      <SearchQueryBar
        query={query}
        onQueryChange={setQuery}
        sort={sort}
        onSortChange={handleSortChange}
        onSubmit={runDiscovery}
        onToggleFilters={() => setFiltersOpen((v) => !v)}
        filtersOpen={filtersOpen}
        activeFilterCount={activeFilterCount}
        isBusy={isBusy}
        canSort={phase === PHASE.READY || phase === PHASE.IDLE}
      />

      {showProgress ? (
        <JobProgress job={job} query={query} onCancel={cancel} />
      ) : (
        <div id="tour-job-progress" className="w-full h-0" />
      )}

      {phase === PHASE.READY && results ? (
        <ResultSummary
          query={query}
          results={results}
          sort={sort}
          filterCount={activeFilterCount}
          selectedId={selectedId}
        />
      ) : null}

      <div className="flex min-h-0 flex-1">
        {/* Below lg the rail is an overlay so the table keeps full width. */}
        {filtersOpen && !isBelowLg ? (
          <FilterRail
            filters={draftFilters}
            onChange={setDraftFilters}
            onClear={clearFilters}
            dirty={dirty}
          />
        ) : null}

        {filtersOpen && isBelowLg ? (
          <div className="fixed inset-0 z-40 flex">
            <button
              type="button"
              className="absolute inset-0 bg-[#000]/70"
              onClick={() => setFiltersOpen(false)}
              aria-label="Close filters"
            />
            <div className="relative ml-auto flex h-full">
              <FilterRail
                filters={draftFilters}
                onChange={setDraftFilters}
                onClear={clearFilters}
                dirty={dirty}
              />
            </div>
          </div>
        ) : null}

        {/* On narrow viewports the inspector takes the region instead of
            splitting it, because a 320px panel beside a dense table is
            unreadable below lg. */}
        {!(isBelowLg && inspectorOpen) ? (
          <section
            id="tour-results-area"
            className="flex min-w-0 flex-1 flex-col overflow-hidden"
            aria-label="Discovery results"
          >
            {phase === PHASE.IDLE ? (
              <EmptyState
                icon={Radar}
                title="No discovery run yet"
                description="Query a competitor ad library to enqueue a scrape. Results are ranked by composite score once the job completes."
                action={
                  <Button size="sm" variant="primary" onClick={runDiscovery}>
                    Run discovery
                  </Button>
                }
              />
            ) : null}

            {phase === PHASE.SUBMITTING ||
            phase === PHASE.RUNNING ||
            phase === PHASE.FETCHING_RESULTS ? (
              <SkeletonRows rows={10} />
            ) : null}

            {phase === PHASE.ERROR ? (
              <ErrorState 
                error={error} 
                onRetry={error?.status === 402 || error?.status === 403 || error?.code === "TRIAL_EXPIRED" || error?.code === "CREDIT_LIMIT_REACHED" ? undefined : retry}
                description={error?.status === 402 || error?.status === 403 || error?.code === "TRIAL_EXPIRED" || error?.code === "CREDIT_LIMIT_REACHED" ? "Upgrade your account or add credits to continue using Discover." : undefined}
              />
            ) : null}

            {phase === PHASE.READY && items.length === 0 ? (
              <EmptyState
                icon={SearchX}
                title="Job completed with no matches"
                description="The scrape ran successfully but nothing in the corpus satisfied the query and filters. Widen the filters and re-run."
                action={
                  <Button size="sm" variant="outline" onClick={clearFilters}>
                    Clear filters
                  </Button>
                }
              />
            ) : null}

            {phase === PHASE.READY && items.length > 0 ? (
              <>
                <ResultsTable
                  items={items}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
                <div className="flex h-8 shrink-0 items-center gap-3 border-t border-border bg-surface px-3">
                  <span className="label-mono">
                    page {results.page} · {formatInt(items.length)} of{" "}
                    {formatInt(results.total)}
                  </span>
                  <div className="ml-auto flex items-center gap-1.5">
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={results.page <= 1}
                      onClick={() => refine({ page: results.page - 1, sort })}
                    >
                      Prev
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={!results.has_more}
                      onClick={() => refine({ page: results.page + 1, sort })}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </>
            ) : null}
          </section>
        ) : null}

        {inspectorOpen ? (
          <CreativeDetailPanel
            creativeId={selectedId}
            onClose={() => setSelectedId(null)}
          />
        ) : null}
      </div>
    </div>
  )
}
