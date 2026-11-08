import { useEffect, useMemo, useState } from "react"
import { Radar, SearchX, Clock, RotateCcw, MessageSquarePlus } from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { useTelemetry } from "@/app/TelemetryContext"
import { SearchQueryBar } from "@/features/discover/SearchQueryBar"
import { FilterRail, countActiveFilters, searchFiltersDiffer } from "@/features/discover/FilterRail"
import { JobProgress } from "@/features/discover/JobProgress"
import { ResultSummary } from "@/features/discover/ResultSummary"
import { ResultsTable } from "@/features/discover/ResultsTable"
import { CreativeDetailPanel } from "@/features/discover/CreativeDetailPanel"
import { Button } from "@/components/ui/Button"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States"
import { PHASE, isServiceRestart, useDiscoverySearch } from "@/hooks/useDiscoverySearch"
import { useIsBelowLg } from "@/hooks/useMediaQuery"
import { useAuth } from "@/context/AuthContext"
import { formatDuration, formatInt } from "@/lib/format"
import { OnboardingTour } from "@/app/OnboardingTour"
import { OnboardingWizardModal } from "@/components/OnboardingWizardModal"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"
import { EntityDossierCard } from "@/features/discover/EntityDossierCard"
import { SavedDraftsModal } from "@/components/SavedDraftsModal"
import w5Discover from "@/i18n/w5Discover"
import { useW8Copy } from "@/i18n/w8Product"

/* Search-time filters (country, status, format, dates, platform, language)
   are sent with the search; run length and the text-rubric minimum
   filter the stored results. Platform, format and spend-band controls were
   removed: every provider is Meta-only and none of them was ever applied. */
const EMPTY_FILTERS = {
  country: "ALL",
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
import { useSearchContext } from "@/context/SearchContext"
import { useLanguage } from "@/context/LanguageContext"

import { Link, useSearchParams } from "react-router-dom"

export function DiscoverPage() {
  const [searchParams] = useSearchParams()
  const { latestSearch, saveCompletedSearch, selectActiveCreative, openSearchSession } = useSearchContext()
  const persistCompletedSearch = /** @type {(search: Record<string, unknown>) => void} */ (saveCompletedSearch)
  const setActiveCreative = /** @type {(creative: object) => void} */ (selectActiveCreative)
  const { t, lang } = useLanguage()
  const copy = w5Discover[lang] ?? w5Discover.en
  const w8 = useW8Copy()
  const [query, setQuery] = useState(() => searchParams.get("q") || latestSearch?.query || "")
  const [queryLanguage, setQueryLanguage] = useState(() => {
    try {
      return localStorage.getItem("helix_search_lang") === "ar" ? "ar" : "en"
    } catch {
      return "en"
    }
  })
  const [sort, setSort] = useState("days_active_desc")
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [showOnboardingModal, setShowOnboardingModal] = useState(false)
  const [tourEnabled, setTourEnabled] = useState(false)
  const [onboardingSaveError, setOnboardingSaveError] = useState(false)
  const [showSupportModal, setShowSupportModal] = useState(false)
  const [showDraftsModal, setShowDraftsModal] = useState(false)

  const isBelowLg = useIsBelowLg()
  const { report } = useTelemetry()
  const { user, completeOnboarding } = useAuth()
  const {
    phase,
    job,
    results,
    error,
    cancelError,
    submit,
    refine,
    cancel,
    retry,
    isBusy,
    isCancelling,
  } =
    useDiscoverySearch()

  useEffect(() => {
    try {
      localStorage.setItem("helix_search_lang", queryLanguage)
    } catch {
      /* ignore */
    }
  }, [queryLanguage])

  /* Search-time filters need a re-run to apply. */
  const dirty = searchFiltersDiffer(draftFilters, appliedFilters)

  const activeFilterCount = useMemo(() => countActiveFilters(draftFilters), [draftFilters])

  /* Sync completed search results with SearchContext across tabs */
  useEffect(() => {
    if (phase === PHASE.READY && results && query) {
      persistCompletedSearch({
        query: query.trim(),
        jobId: job?.job_id,
        total: results.total,
        items: results.items,
        tookMs: results.took_ms,
      })
    }
  }, [phase, results, query, job?.job_id, persistCompletedSearch])

  /* Sync active creative */
  useEffect(() => {
    if (selectedId && results?.items) {
      const active = results.items.find((i) => i.id === selectedId)
      if (active) setActiveCreative(active)
    }
  }, [selectedId, results?.items, selectActiveCreative])

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

  useEffect(() => {
    if (user && user.has_completed_onboarding === false) {
      setShowOnboardingModal(true)
      setTourEnabled(false)
    }
  }, [user])

  const handleCloseOnboarding = (searchBrand) => {
    setShowOnboardingModal(false)
    if (searchBrand) {
      setQuery(searchBrand)
      submit({
        query: searchBrand,
        filters: appliedFilters,
        sort,
        query_language: queryLanguage,
      })
    }
    // Start the tour guide right after questionnaire finishes
    setTimeout(() => {
      setTourEnabled(true)
    }, 200)
  }

  async function finishOnboarding() {
    setTourEnabled(false)
    try {
      await completeOnboarding()
      setOnboardingSaveError(false)
    } catch {
      setOnboardingSaveError(true)
    }
  }

  function handleDismissOnboarding() {
    setShowOnboardingModal(false)
    void finishOnboarding()
  }

  function runDiscovery() {
    if (!query.trim()) return
    setSelectedId(null)
    setAppliedFilters(draftFilters)
    submit({ query: query.trim(), filters: draftFilters, sort, query_language: queryLanguage })
  }

  function handleSortChange(next) {
    setSort(next)
    if (phase === PHASE.READY) refine({ page: 1, sort: next })
  }

  /* Run length and rubric minimum apply instantly to stored results. */
  function handleFiltersChange(next) {
    setDraftFilters(next)
    const viewChanged =
      (next.min_days_active ?? 0) !== (appliedFilters.min_days_active ?? 0) ||
      (next.min_score ?? 0) !== (appliedFilters.min_score ?? 0)
    if (!viewChanged) return
    setAppliedFilters((prev) => ({ ...prev, min_days_active: next.min_days_active ?? 0, min_score: next.min_score ?? 0 }))
    if (phase === PHASE.READY) {
      setSelectedId(null)
      refine({ page: 1, view: { min_days: next.min_days_active ?? 0, min_score: next.min_score ?? 0 } })
    }
  }

  function clearFilters() {
    handleFiltersChange(EMPTY_FILTERS)
  }

  const displayResults = results || (phase === PHASE.IDLE && latestSearch?.items?.length ? {
    total: latestSearch.total || latestSearch.items.length,
    items: latestSearch.items,
    took_ms: latestSearch.tookMs || 0,
    page: 1,
  } : null)
  const displayJob = job || (phase === PHASE.IDLE && latestSearch?.entity_profile ? {
    job_id: latestSearch.jobId,
    entity_profile: latestSearch.entity_profile,
    stage_label: "Saved Search Session",
    stage: "complete",
    records_found: latestSearch.total || latestSearch.items?.length || 0,
  } : job)

  const items = displayResults?.items ?? []
  /* Zero-result honesty: the results endpoint never applies the filter
     rail, so an empty set almost always means the scrape itself found
     nothing — the backend's zero_results stage_label says exactly why. */
  const scrapedNothing =
    phase === PHASE.READY && items.length === 0 && (job?.records_found ?? 0) === 0
  const filtersWereApplied = countActiveFilters(appliedFilters) > 0
  const showProgress = Boolean(job) && phase !== PHASE.READY && phase !== PHASE.IDLE
  const inspectorOpen = Boolean(selectedId)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <OnboardingTour 
        user={user} 
        enabled={tourEnabled} 
        onComplete={finishOnboarding}
      />
      {onboardingSaveError && <div role="alert" className="flex items-center gap-3 border-b border-border bg-surface p-3 text-sm"><span>{t("onboardingSaveFailed")}</span><Button onClick={finishOnboarding}>{t("retry")}</Button></div>}
      <BreadcrumbBar
        className=""
        trail={[copy.discovery, copy.liveSearch, query ? `"${query}"` : null].filter(Boolean)}
        meta={
          phase === PHASE.READY && results
            ? `${formatInt(results?.total ?? 0)} records · ${formatDuration(
                results?.took_ms ?? 0,
              )}`
            : displayResults && phase === PHASE.IDLE
            ? `${formatInt(displayResults.total)} records (saved)`
            : null
        }
        actions={
              <Button
            size="xs"
            variant="ghost"
            onClick={() => setShowSupportModal(true)}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-text"
          >
            <MessageSquarePlus className="w-3.5 h-3.5 text-teal-400" />
            {t("reportIssue", copy.reportIssue)}
          </Button>
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
        queryLanguage={queryLanguage}
        onQueryLanguageChange={setQueryLanguage}
        onOpenDrafts={() => setShowDraftsModal(true)}
      />

      {showProgress ? (
        <JobProgress
          job={job}
          query={query}
          onCancel={cancel}
          onRetry={retry}
          cancelError={cancelError}
          isCancelling={isCancelling}
          showRetry={phase === PHASE.TIMED_OUT}
        />
      ) : (
        <div id="tour-job-progress" className="w-full h-0" />
      )}

      {(phase === PHASE.READY || (phase === PHASE.IDLE && displayResults)) && displayResults ? (
        <ResultSummary
          query={query || latestSearch?.query || ""}
          results={displayResults}
          sort={sort}
          filterCount={activeFilterCount}
          hiddenUnknown={displayResults?.hidden_unknown_run_length ?? null}
          selectedId={selectedId}
        />
      ) : null}

      <div className="flex min-h-0 flex-1">
        {/* Below lg the rail is an overlay so the table keeps full width. */}
        {filtersOpen && !isBelowLg ? (
          <FilterRail
            filters={draftFilters}
            onChange={handleFiltersChange}
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
                onChange={handleFiltersChange}
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
            className="flex min-w-0 flex-1 flex-col overflow-y-auto overflow-x-hidden"
            aria-label={t("discoveryResults")}
          >
            {phase === PHASE.IDLE && items.length === 0 && !displayJob?.entity_profile && latestSearch?.query ? (
              <EmptyState
                icon={SearchX}
                size="lg"
                status={w8.discoverLastEmptyStatus}
                title={w8.discoverLastEmptyTitle(latestSearch.query)}
                description={w8.discoverLastEmptyBody}
                action={
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => {
                      const again = query.trim() || latestSearch.query
                      setQuery(again)
                      setAppliedFilters(draftFilters)
                      submit({ query: again, filters: draftFilters, sort, query_language: queryLanguage })
                    }}
                  >
                    {w8.discoverLastEmptyCta}
                  </Button>
                }
              />
            ) : null}

            {phase === PHASE.IDLE && items.length === 0 && !displayJob?.entity_profile && !latestSearch?.query ? (
              <EmptyState
                icon={Radar}
                size="lg"
                status={w8.discoverEmptyStatus}
                title={w8.discoverEmptyTitle}
                description={w8.discoverEmptyBody}
                action={
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => (query.trim() ? runDiscovery() : document.getElementById("tour-search-input")?.focus())}
                    className="">
                    {w8.discoverEmptyCta}
                  </Button>
                }
               className=""/>
            ) : null}

            {phase === PHASE.IDLE && items.length === 0 && displayJob?.entity_profile ? (
              <div className="flex flex-1 flex-col overflow-y-auto">
                <EntityDossierCard profile={displayJob.entity_profile} query={query || latestSearch?.query} isZeroResults={true} />
              </div>
            ) : null}

            {phase === PHASE.SUBMITTING ||
            phase === PHASE.RUNNING ||
            phase === PHASE.FETCHING_RESULTS ? (
              <SkeletonRows rows={10}  className=""/>
            ) : null}

            {phase === PHASE.ERROR && isServiceRestart(error) ? (
              <EmptyState
                icon={RotateCcw}
                status="interrupted"
                title={copy.serviceRestarted}
                description={copy.serviceRestartedDescription}
                action={
                  <Button size="sm" variant="primary" onClick={retry} className="">
                    {copy.runSearchAgain}
                  </Button>
                }
               className=""/>
            ) : null}

            {phase === PHASE.ERROR && !isServiceRestart(error) ? (
              <ErrorState
                error={error}
                onRetry={error?.status === 402 || error?.status === 403 || error?.code === "CREDIT_LIMIT_REACHED" ? undefined : retry}
                description={
                  error?.status === 402 || error?.status === 403 || error?.code === "CREDIT_LIMIT_REACHED"
                    ? t("discoverNeedsAccess")
                    : error?.code === "discover_paused"
                      ? w8.discoverPaused
                      : error?.code === "query_too_long"
                        ? w8.discoverQueryTooLong
                        : error?.code === "daily_search_cap_reached"
                          ? w8.discoverSearchCap
                          : undefined
                }
                action={error?.status === 402 || error?.status === 403 || error?.code === "CREDIT_LIMIT_REACHED" ? (
                  <Button as={Link} to="/access" size="sm" variant="primary">{w8.discoverOpenAccess}</Button>
                ) : undefined}
                className=""
              />
            ) : null}

            {phase === PHASE.TIMED_OUT && !job ? (
              <EmptyState
                icon={Clock}
                size="lg"
                status={t("stalled")}
                title={t("takingLonger")}
                description={cancelError ? copy.timeoutNoJob : t("takingLongerDesc")}
                action={
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="primary" onClick={retry} className="">
                      {copy.retrySearch}
                    </Button>
                  </div>
                }
               className=""/>
            ) : null}

            {phase === PHASE.READY && items.length === 0 ? (
              displayJob?.entity_profile ? (
                <div className="flex flex-1 flex-col overflow-y-auto">
                  <EntityDossierCard profile={displayJob.entity_profile} query={query} isZeroResults={true} />
                  <div className="flex flex-col items-center justify-center p-8 text-center">
                    <p className="max-w-md text-xs leading-relaxed text-text-muted">
                      {displayJob?.stage_label && displayJob.stage_label !== "complete"
                        ? displayJob.stage_label
                        : t("noMetaAdsNotice")}
                    </p>
                    {filtersWereApplied ? (
                      <Button size="sm" variant="outline" onClick={clearFilters} className="mt-3">
                        {t("clearFilters")}
                      </Button>
                    ) : null}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={SearchX}
                  size="lg"
                status={scrapedNothing ? copy.statusZeroResults : copy.statusNoMatches}
                  title={
                    scrapedNothing
                      ? t("zeroResultsTitle")
                      : t("noMatchesTitle")
                  }
                  description={
                    scrapedNothing
                      ? displayJob?.stage_label && displayJob?.stage !== "complete"
                        ? displayJob.stage_label
                        : 'The ad libraries had no active ads for this query. Try a company domain (e.g. "nike.com") or a broader industry keyword, then re-run.'
                      : t("noMatchesDesc")
                  }
                  action={
                    filtersWereApplied ? (
                      <Button size="sm" variant="outline" onClick={clearFilters} className="">
                        {t("clearFilters")}
                      </Button>
                    ) : null
                  }
                 className=""/>
              )
            ) : null}

            {(phase === PHASE.READY || (phase === PHASE.IDLE && items.length > 0)) && items.length > 0 ? (
              <>
                {displayJob?.entity_profile ? (
                  <EntityDossierCard profile={displayJob.entity_profile} query={query || latestSearch?.query} isZeroResults={false} />
                ) : null}
                <ErrorBoundary variant="compact" label="The results table">
                  <ResultsTable
                    items={items}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                  />
                </ErrorBoundary>
                <div className="flex h-8 shrink-0 items-center gap-3 border-t border-border bg-surface px-3">
                  <span className="label-mono">
                    page {displayResults?.page || 1} · {formatInt(items.length)} of{" "}
                    {formatInt(displayResults?.total || items.length)}
                    {phase === PHASE.IDLE && (
                      <span className="ml-2 text-accent font-mono text-[10px]">(Saved Session)</span>
                    )}
                  </span>
                  <div className="ml-auto flex items-center gap-1.5">
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={!displayResults?.page || displayResults.page <= 1 || phase === PHASE.IDLE}
                      onClick={() => refine({ page: (displayResults?.page || 1) - 1, sort })}
                     className="">
                      Prev
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={!displayResults?.has_more || phase === PHASE.IDLE}
                      onClick={() => refine({ page: (displayResults?.page || 1) + 1, sort })}
                     className="">
                      Next
                    </Button>
                  </div>
                </div>
              </>
            ) : null}
          </section>
        ) : null}

        {inspectorOpen ? (
          <ErrorBoundary variant="compact" label="The creative detail panel">
            <CreativeDetailPanel
              creativeId={selectedId}
              onClose={() => setSelectedId(null)}
            />
          </ErrorBoundary>
        ) : null}
      </div>

      <OnboardingWizardModal
        isOpen={showOnboardingModal}
        onClose={handleCloseOnboarding}
        onDismiss={handleDismissOnboarding}
        onSearchSelect={(searchBrand) => setQuery(searchBrand)}
      />

      <SupportFeedbackModal
        isOpen={showSupportModal}
        onClose={() => setShowSupportModal(false)}
        initialContext={{ page: "Discover", query, tag: "discover" }}
        onSuccess={() => setShowSupportModal(false)}
      />

      <SavedDraftsModal
        isOpen={showDraftsModal}
        onClose={() => setShowDraftsModal(false)}
        currentQuery={query}
        currentFilters={draftFilters}
        onSelectSearch={async (item) => {
          setQuery(item.query)
          setSelectedId(null)
          const opened = await openSearchSession(item).catch(() => false)
          // Nothing stored to show (failed or empty): run it again.
          if (!opened) {
            setAppliedFilters(draftFilters)
            submit({ query: item.query, filters: draftFilters, sort, query_language: queryLanguage })
          }
        }}
        onSelectDraft={(draft) => {
          setQuery(draft.query || draft.title)
          const next = { ...EMPTY_FILTERS, ...(draft.filters || {}) }
          setDraftFilters(next)
          setAppliedFilters(next)
        }}
      />
    </div>
  )
}

export default DiscoverPage
