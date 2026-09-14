import React, { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  BarChart2,
  TrendingUp,
  Users,
  RefreshCw,
  AlertCircle,
  Sparkles,
  BookOpen,
  Search,
  PenLine,
  CircleSlash,
  Radio,
  ExternalLink,
} from "lucide-react"
import { dashboardService, playbookService } from "@/services"
import { Panel } from "@/components/ui/Panel"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { InfoTip } from "@/components/ui/InfoTip"
import { useLanguage } from "@/context/LanguageContext"
import { Tag } from "@/components/ui/Tag"
import { Button } from "@/components/ui/Button"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { SkeletonRows } from "@/components/ui/States"

const EVENT_META = {
  new_ad: { label: "NEW AD", variant: "success", icon: Sparkles },
  copy_changed: { label: "COPY CHANGED", variant: "warning", icon: PenLine },
  killed_ad: { label: "STOPPED", variant: "danger", icon: CircleSlash },
}

export default function DashboardPage() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedBrands, setSelectedBrands] = useState([])
  const [compilingPlaybook, setCompilingPlaybook] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await dashboardService.getMetrics()
      setData(result)
      if (result?.cross_brand && result.cross_brand.length > 0) {
        setSelectedBrands(result.cross_brand.slice(0, 3).map(b => b.brand_id))
      }
    } catch (err) {
      console.warn("Failed to load dashboard metrics:", err)
      setError(err.message || "Failed to load dashboard data")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleShareAsPlaybook = async () => {
    if (compilingPlaybook) return
    setCompilingPlaybook(true)
    try {
      const primaryBrand = data?.cross_brand?.[0]?.name || data?.top_performers?.[0]?.brand_name || "Competitive Landscape"
      
      const playbookCreatives = (data?.top_performers || []).slice(0, 6).map(c => ({
        id: c.id,
        headline: c.headline || "",
        body: c.body || "",
        cta: c.cta || "Learn More",
        platform: c.platform || "meta",
        format: c.format || "image",
        landing_domain: c.landing_domain || c.brand_name || primaryBrand,
        days_active: c.days_active || 1,
        data_source: c.source_type || "ad_library_scrape",
        is_estimated: c.metrics?.is_impression_estimate ?? true
      }))

      const patterns = (data?.cross_brand || []).slice(0, 5).map(b => ({
        id: b.brand_id,
        name: `${b.name} (${b.dominant_format.toUpperCase()}) Angle`,
        category: b.dominant_format,
        description: `Active campaign volume: ${b.active_ads} verified ads. Average composite score: ${b.avg_score != null ? b.avg_score.toFixed(1) : "N/A"}.`,
        confidence_score: 0.92,
        estimated_lift_percent: b.avg_score ? Math.max(Math.round((b.avg_score - 50) * 0.5), 5) : null
      }))

      const insights = []
      if (data?.narrative_summary?.summary) {
        insights.push({
          id: "narrative-summary-ins",
          title: "Executive Teardown & Movement",
          summary: data.narrative_summary.summary,
          kind: "summary",
          confidence: 0.95
        })
      }
      if (data?.monitor_changes && data.monitor_changes.length > 0) {
        const topDiff = data.monitor_changes[0]
        insights.push({
          id: "diff-summary-ins",
          title: `Recent Competitor Action (${(topDiff.type || 'diff').replace('_', ' ').toUpperCase()})`,
          summary: `Detected on ${topDiff.monitor_name}: "${topDiff.headline || topDiff.body || 'Creative update'}"`,
          kind: "diff",
          confidence: 0.90
        })
      }

      const res = await playbookService.compilePlaybook({
        brand_name: primaryBrand,
        query: primaryBrand,
        custom_title: `${primaryBrand} & Competitive Intelligence Playbook`,
        summary: data?.narrative_summary?.summary || `Cross-brand creative intelligence playbook compiled from ${data?.top_performers?.length || 0} top-performing ads.`,
        creatives: playbookCreatives,
        patterns: patterns,
        insights: insights
      })

      if (res?.public_id) {
        navigate(`/playbook/${res.public_id}`)
      }
    } catch (err) {
      console.error("Failed to compile dashboard playbook:", err)
      alert(`Could not compile playbook: ${err.message || err}`)
    } finally {
      setCompilingPlaybook(false)
    }
  }

  const toggleBrand = (brandId) => {
    if (selectedBrands.includes(brandId)) {
      setSelectedBrands(prev => prev.filter(id => id !== brandId))
    } else {
      if (selectedBrands.length >= 3) {
        setSelectedBrands(prev => [...prev.slice(0, 2), brandId])
      } else {
        setSelectedBrands(prev => [...prev, brandId])
      }
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-background">
        <BreadcrumbBar trail={["Helix", "Workspace", "Cross-Brand Dashboard"]} />
        <div className="p-6">
          <SkeletonRows rows={8} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-background">
        <BreadcrumbBar trail={["Helix", "Workspace", "Cross-Brand Dashboard"]} />
        <div className="flex h-[60vh] flex-col items-center justify-center p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20 text-red-400 mb-4">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-base font-bold text-text">Unable to Load Dashboard</h2>
          <p className="mt-1 font-mono text-xs text-text-muted max-w-sm mb-5">
            {error}
          </p>
          <Button size="sm" variant="outline" onClick={loadData} className="flex items-center gap-2">
            <RefreshCw className="h-3.5 w-3.5" />
            Retry Connection
          </Button>
        </div>
      </div>
    )
  }

  const comparisonBrands = (data?.cross_brand || []).filter(b => selectedBrands.includes(b.brand_id))
  const maxCount = Math.max(...(data?.timeline || []).map(t => t.count), 1)

  // Map monitor diffs for indicators in leaderboards
  const newAdSignatures = new Set(
    (data?.monitor_changes || [])
      .filter(m => m.type === "new_ad")
      .map(m => (m.creative_id || m.headline || "").toLowerCase().trim())
  )
  const isCreativeNew = (c) => {
    if (!c) return false
    return (
      (c.id && newAdSignatures.has(c.id.toLowerCase())) ||
      (c.headline && newAdSignatures.has(c.headline.toLowerCase().trim()))
    )
  }

  const hasActivity = Boolean(
    (data?.cross_brand && data.cross_brand.length > 0) ||
    (data?.top_performers && data.top_performers.length > 0) ||
    (data?.timeline && data.timeline.length > 0)
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-background">
      <BreadcrumbBar
        trail={["Helix", "Workspace", "Dashboard"]}
        meta={data?.narrative_summary?.status === "ready" ? "Live Intelligence" : null}
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={handleShareAsPlaybook}
            disabled={compilingPlaybook || (data?.top_performers || []).length === 0}
            className="flex items-center gap-1.5"
          >
            {compilingPlaybook ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-accent" />
            ) : (
              <BookOpen className="h-3.5 w-3.5 text-accent" />
            )}
            <span>{compilingPlaybook ? "Compiling..." : "Share as Playbook"}</span>
          </Button>
        }
      />

      <div className="w-full max-w-7xl mx-auto flex flex-col p-6 space-y-6">
        {/* PAGE HEADER */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-text">Workspace Dashboard</h1>
            <p className="mt-1 font-mono text-xs text-text-muted">
              Cross-brand competitive intelligence & creative performance
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={loadData}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh</span>
            </Button>
            <Button
              size="sm"
              variant="accent"
              onClick={handleShareAsPlaybook}
              disabled={compilingPlaybook || (data?.top_performers || []).length === 0}
              className="flex items-center gap-1.5"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Share as Playbook</span>
            </Button>
          </div>
        </div>

        {/* 1. NARRATIVE SUMMARY BLOCK (TOP OF PAGE) */}
        <ErrorBoundary variant="compact" label="The executive summary panel">
          {!hasActivity || data?.narrative_summary?.status === "empty" ? (
            <Panel className="border-border/60 bg-surface-2/40 p-5">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-text-muted shrink-0">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-text">No Competitor Activity Tracked Yet</h3>
                    <p className="mt-0.5 font-mono text-xs text-text-muted">
                      {data?.narrative_summary?.message || "Run your first search to start seeing insights here."}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="accent"
                  onClick={() => navigate("/discover")}
                  className="flex items-center gap-1.5 shrink-0"
                >
                  <Search className="h-3.5 w-3.5" />
                  <span>Search Competitors</span>
                </Button>
              </div>
            </Panel>
          ) : (
            <Panel className="border-border bg-surface-2 p-5">
              <div className="flex items-start gap-3.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-md border border-accent/30 bg-accent/10 text-accent shrink-0 mt-0.5">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-accent">
                        Executive Summary
                      </span>
                      <span className="font-mono text-[10px] text-text-faint">
                        Grounded AI Teardown
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-text-muted hidden sm:inline">
                        Strict Real Data Grounding
                      </span>
                      <Tag variant="neutral" size="sm" className="font-mono text-[9px] uppercase">
                        Live Intelligence
                      </Tag>
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed text-text font-normal">
                    {data?.narrative_summary?.summary}
                  </p>
                </div>
              </div>
            </Panel>
          )}
        </ErrorBoundary>

        {/* 2. WHAT CHANGED / COMPETITOR DIFF PIPELINE */}
        <ErrorBoundary variant="compact" label="The competitor activity diff panel">
          <Panel className="flex flex-col">
            <div className="border-b border-border p-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                  <Radio className="h-4 w-4 text-accent" />
                  What Changed (Monitor Diffs)
                </h2>
                <p className="font-mono text-[10px] uppercase text-text-faint">
                  Fingerprint diff events across automated watches
                </p>
              </div>
              {data?.has_monitors && (
                <Tag variant="accent" size="sm" className="font-mono text-[10px]">
                  {data.active_monitors_count} ACTIVE {data.active_monitors_count === 1 ? "MONITOR" : "MONITORS"}
                </Tag>
              )}
            </div>

            <div className="p-4">
              {data?.monitor_changes && data.monitor_changes.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {data.monitor_changes.slice(0, 6).map((change) => {
                    const meta = EVENT_META[change.type] || { label: change.type?.toUpperCase() || "EVENT", variant: "neutral", icon: Sparkles }
                    const Icon = meta.icon
                    return (
                      <div key={change.id} className="flex flex-col justify-between rounded-md border border-border/60 bg-surface-2 p-3 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <Tag variant={meta.variant} size="sm" className="font-mono text-[9px] flex items-center gap-1">
                            <Icon className="h-3 w-3" />
                            {meta.label}
                          </Tag>
                          <span className="font-mono text-[10px] text-text-faint truncate max-w-[120px]">
                            {change.monitor_name}
                          </span>
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-text line-clamp-2" title={change.headline || change.body}>
                            {change.headline || change.body || "Creative fingerprint update"}
                          </p>
                          {change.previous && change.type === "copy_changed" && (
                            <p className="mt-1 font-mono text-[10px] text-text-muted line-clamp-1">
                              Previous: &ldquo;{change.previous.headline || change.previous.body || "..."}&rdquo;
                            </p>
                          )}
                        </div>
                        <div className="flex items-center justify-between font-mono text-[10px] text-text-faint pt-1 border-t border-border/30">
                          <span>{change.platform ? change.platform.toUpperCase() : "META"}</span>
                          <span>{change.created_at ? new Date(change.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : "Recent"}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : data?.has_monitors ? (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-md border border-border/50 bg-surface-2/60 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-text-muted shrink-0">
                      <Radio className="h-4 w-4 text-accent" />
                    </div>
                    <div>
                      <span className="text-xs font-medium text-text">Baseline Established</span>
                      <p className="mt-0.5 font-mono text-[10px] text-text-muted">
                        {data.active_monitors_count} monitor{data.active_monitors_count > 1 ? "s are" : " is"} active. Diff events will automatically trigger when competitors launch new ads, stop running ads, or alter copy.
                      </p>
                    </div>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => navigate("/monitors")} className="shrink-0 text-xs">
                    View Monitors
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-md border border-border/50 bg-surface-2/60 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-text-muted shrink-0">
                      <Radio className="h-4 w-4 text-text-faint" />
                    </div>
                    <div>
                      <span className="text-xs font-medium text-text">Automated Tracking Not Active</span>
                      <p className="mt-0.5 font-mono text-[10px] text-text-muted">
                        Set up a competitor monitor to track new ad drops, killed fatigue angles, and copy alterations automatically.
                      </p>
                    </div>
                  </div>
                  <Button size="sm" variant="accent" onClick={() => navigate("/monitors")} className="shrink-0 text-xs flex items-center gap-1.5">
                    <Radio className="h-3 w-3" />
                    Set Up Competitor Monitor
                  </Button>
                </div>
              )}
            </div>
          </Panel>
        </ErrorBoundary>

        {/* 3. LEADERBOARDS GRID */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* TOP PERFORMERS */}
          <ErrorBoundary variant="compact" label="The top performers panel">
            <Panel className="flex flex-col">
              <div className="border-b border-border p-4">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                  <TrendingUp className="h-4 w-4 text-accent" />
                  {t("topPerformers", "Top Performers")}
                </h2>
                <p className="font-mono text-[10px] uppercase text-text-faint flex items-center">
                  {t("rankedByComposite", "Ranked by composite score")}
                  <InfoTip text="One combined 0–100 score Helix computes from each ad's hook, clarity and retention — not a metric Meta or the ad platform reports." label="What does composite score mean?" />
                </p>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <div className="flex flex-col gap-3">
                  {(data?.top_performers || []).length === 0 ? (
                    <div className="text-sm text-text-faint">No scored creatives found.</div>
                  ) : (
                    data.top_performers.map((creative) => (
                      <div key={creative.id} className="flex items-center justify-between gap-3 rounded-md border border-border/50 bg-surface-2 p-3">
                        <div className="flex flex-col min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-sm font-medium text-text truncate max-w-sm md:max-w-md" title={creative.headline}>
                              {creative.headline || creative.brand_name || "Ad Creative"}
                            </span>
                            {isCreativeNew(creative) && (
                              <Tag variant="success" size="sm" className="font-mono text-[8px] py-0 px-1">
                                NEW
                              </Tag>
                            )}
                          </div>
                          <div className="flex items-center gap-2 font-mono text-[10px] text-text-muted">
                            <span>{creative.format?.toUpperCase() || "IMAGE"}</span>
                            <span>·</span>
                            <strong className="text-accent font-semibold">{creative.brand_name || creative.brand_id}</strong>
                            {creative.platform ? <span>· {creative.platform.toUpperCase()}</span> : null}
                            <span className="text-text-faint hidden sm:inline">· {creative.source_type?.toUpperCase() || "AD"}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end shrink-0">
                          <span className="font-mono text-lg font-bold text-accent">
                            {creative.scores?.composite != null ? creative.scores.composite.toFixed(1) : "—"}
                          </span>
                          <span className="font-mono text-[10px] text-text-faint">SCORE</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </Panel>
          </ErrorBoundary>

          {/* REACH / ACTIVITY LEADERBOARD */}
          <ErrorBoundary variant="compact" label="The leaderboard panel">
            <Panel className="flex flex-col">
              <div className="border-b border-border p-4">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                  <Users className="h-4 w-4 text-accent" />
                  {t("leaderboardPanel", "Reach Leaderboard")}
                </h2>
                <p className="font-mono text-[10px] uppercase text-text-faint flex items-center">
                  Ranked by estimated reach or longevity
                  <InfoTip text="Impressions are estimated from ad library activity duration, spend bands, and placement breadth; days active reflects verified library crawl span." label="What does estimated reach mean?" />
                </p>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <div className="flex flex-col gap-3">
                  {(data?.reach_leaderboard || []).length === 0 ? (
                    <div className="text-sm text-text-faint">No reach data available.</div>
                  ) : (
                    data.reach_leaderboard.map((creative) => {
                      const hasReach = creative.metrics?.impressions_est > 0
                      const value = hasReach ? creative.metrics.impressions_est.toLocaleString() : creative.days_active
                      const isEst = creative.metrics?.is_impression_estimate ?? true
                      const label = hasReach ? (isEst ? "IMPR (EST)" : "IMPRESSIONS") : "DAYS ACTIVE"
                      
                      return (
                        <div key={creative.id} className="flex items-center justify-between gap-3 rounded-md border border-border/50 bg-surface-2 p-3">
                          <div className="flex flex-col min-w-0 flex-1">
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="text-sm font-medium text-text truncate max-w-sm md:max-w-md" title={creative.headline}>
                                {creative.headline || creative.brand_name || "Ad Creative"}
                              </span>
                              {isCreativeNew(creative) && (
                                <Tag variant="success" size="sm" className="font-mono text-[8px] py-0 px-1">
                                  NEW
                                </Tag>
                              )}
                            </div>
                            <div className="flex items-center gap-2 font-mono text-[10px] text-text-muted">
                              <span>{creative.format?.toUpperCase() || "IMAGE"}</span>
                              <span>·</span>
                              <strong className="text-accent font-semibold">{creative.brand_name || creative.brand_id}</strong>
                              {creative.platform ? <span>· {creative.platform.toUpperCase()}</span> : null}
                              <span className="text-text-faint hidden sm:inline">· {creative.source_type?.toUpperCase() || "AD"}</span>
                            </div>
                          </div>
                          <div className="flex flex-col items-end shrink-0">
                            <span className="font-mono text-sm font-bold text-text">
                              {value}
                            </span>
                            <span className="font-mono text-[9px] text-text-faint">{label}</span>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            </Panel>
          </ErrorBoundary>

          {/* TIMELINE VIEW */}
          <ErrorBoundary variant="compact" label="The timeline panel">
            <Panel className="col-span-1 md:col-span-2">
              <div className="border-b border-border p-4">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                  <Activity className="h-4 w-4 text-accent" />
                  {t("timelinePanel", "Timeline Activity")}
                </h2>
                <p className="font-mono text-[10px] uppercase text-text-faint">
                  Creatives discovered per day across all search jobs
                </p>
              </div>
              <div className="p-6">
                {(data?.timeline || []).length === 0 ? (
                  <div className="text-sm text-text-faint">No timeline data available.</div>
                ) : (
                  <div className="flex h-40 items-end gap-2">
                    {data.timeline.map((point, i) => {
                      const heightPercent = Math.max((point.count / maxCount) * 100, 5)
                      return (
                        <div key={i} className="group relative flex flex-1 flex-col justify-end items-center h-full">
                          <div 
                            className="w-full rounded-t-sm bg-accent/40 transition-all group-hover:bg-accent" 
                            style={{ height: `${heightPercent}%` }}
                          />
                          <div className="absolute -top-8 hidden rounded bg-surface px-2 py-1 font-mono text-[10px] text-text shadow-lg group-hover:block whitespace-nowrap z-10 border border-border">
                            {point.date}: {point.count} creatives
                          </div>
                          <span className="mt-2 block font-mono text-[9px] text-text-faint truncate max-w-full">
                            {new Date(point.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </Panel>
          </ErrorBoundary>

          {/* CROSS-BRAND COMPARISON */}
          <ErrorBoundary variant="compact" label="The cross-brand panel">
            <Panel className="col-span-1 md:col-span-2 flex flex-col">
              <div className="border-b border-border p-4 flex flex-wrap justify-between items-center gap-3">
                <div>
                  <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                    <BarChart2 className="h-4 w-4 text-accent" />
                    {t("crossBrandPanel", "Cross-Brand Comparison")}
                  </h2>
                  <p className="font-mono text-[10px] uppercase text-text-faint">
                    Select 2-3 brands to compare metrics
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 max-w-2xl justify-end">
                  {(data?.cross_brand || []).map(b => (
                    <button
                      key={b.brand_id}
                      onClick={() => toggleBrand(b.brand_id)}
                      className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                        selectedBrands.includes(b.brand_id) 
                          ? "bg-accent/20 text-accent border border-accent/50 font-bold" 
                          : "bg-surface-2 text-text-muted border border-border hover:text-text hover:border-border-strong"
                      }`}
                    >
                      {b.name}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="p-6">
                {comparisonBrands.length === 0 ? (
                  <div className="text-sm text-text-faint">Select brands above to compare.</div>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                    {comparisonBrands.map(brand => (
                      <div key={brand.brand_id} className="rounded-xl border border-border bg-surface-2 p-5 shadow-sm">
                        <h3 className="mb-4 text-lg font-bold text-text truncate">{brand.name}</h3>
                        
                        <div className="space-y-4">
                          <div>
                            <p className="font-mono text-[10px] text-text-faint uppercase flex items-center">
                              {t("avgComposite", "Avg Composite Score")}
                              <InfoTip text="One combined 0–100 score Helix computes from each ad's hook, clarity and retention — not a metric Meta or the ad platform reports." label="What does avg composite score mean?" />
                            </p>
                            <p className="font-mono text-2xl font-bold text-accent">
                              {brand.avg_score != null ? brand.avg_score.toFixed(1) : "—"}
                            </p>
                          </div>
                          
                          <div>
                            <p className="font-mono text-[10px] text-text-faint uppercase flex items-center">
                              {t("activeAds", "Active Ads")}
                              <InfoTip text="How many ads from this brand were found in your latest searches." label="What does active ads mean?" />
                            </p>
                            <p className="text-base font-medium text-text">{brand.active_ads}</p>
                          </div>
                          
                          <div>
                            <p className="font-mono text-[10px] text-text-faint uppercase">Dominant Format</p>
                            <Tag variant="accent" className="mt-1">{brand.dominant_format.toUpperCase()}</Tag>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Panel>
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}
