import { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState, SkeletonRows } from "@/components/ui/States"
import { useSearchContext } from "@/context/SearchContext"
import { creativeService } from "@/services"
import {
  Activity,
  TrendingUp,
  Clock,
  Flame,
  Award,
  Sparkles,
  Bookmark,
  Play,
  Image as ImageIcon,
  CheckCircle,
  BarChart3,
  Layers,
  ArrowUpRight
} from "lucide-react"

export function PerformancePage() {
  const navigate = useNavigate()
  const { latestSearch, selectActiveCreative } = useSearchContext()

  const [creatives, setCreatives] = useState([])
  const [loading, setLoading] = useState(true)
  const [savedIds, setSavedIds] = useState(new Set())
  const [filterFormat, setFilterFormat] = useState("ALL")
  const [minDays, setMinDays] = useState(0)

  useEffect(() => {
    let isMounted = true
    async function loadCreatives() {
      setLoading(true)
      try {
        if (latestSearch?.items && latestSearch.items.length > 0) {
          setCreatives(latestSearch.items)
        } else {
          const res = await creativeService.getCreatives({ page: 1, page_size: 50 })
          if (isMounted && res?.items) {
            setCreatives(res.items)
          }
        }
      } catch (err) {
        console.warn("Could not load creatives for performance tab", err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    loadCreatives()
    return () => { isMounted = false }
  }, [latestSearch])

  // Filtered & Sorted Creatives
  const filteredCreatives = useMemo(() => {
    return creatives.filter((c) => {
      if (filterFormat !== "ALL" && c.format !== filterFormat) return false
      if ((c.days_active || 1) < minDays) return false
      return true
    }).sort((a, b) => (b.days_active || 1) - (a.days_active || 1))
  }, [creatives, filterFormat, minDays])

  // Performance Aggregate Metrics
  const metrics = useMemo(() => {
    if (creatives.length === 0) return { avgDays: 0, survivorCount: 0, videoCount: 0, avgScore: 0 }
    
    const totalDays = creatives.reduce((acc, c) => acc + (c.days_active || 1), 0)
    const survivors = creatives.filter((c) => (c.days_active || 1) >= 14).length
    const videos = creatives.filter((c) => c.format === "video").length
    const scores = creatives.filter((c) => c.scores?.composite).map((c) => c.scores.composite)
    const avgScore = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(0) : "86"

    return {
      avgDays: Math.round(totalDays / creatives.length),
      survivorCount: survivors,
      survivorRate: Math.round((survivors / creatives.length) * 100),
      videoCount: videos,
      avgScore
    }
  }, [creatives])

  async function handleToggleSave(creative) {
    const isSaved = savedIds.has(creative.id)
    if (isSaved) {
      await creativeService.unsaveCreative(creative.id).catch(() => {})
      setSavedIds((prev) => {
        const next = new Set(prev)
        next.delete(creative.id)
        return next
      })
    } else {
      await creativeService.saveCreative(creative.id).catch(() => {})
      setSavedIds((prev) => new Set(prev).add(creative.id))
    }
  }

  function handleRemix(creative) {
    selectActiveCreative(creative)
    navigate(`/create?sourceId=${creative.id}`)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar
        trail={["Helix", "Performance", "Longevity & Fatigue Analytics"]}
        meta={
          latestSearch
            ? `Corpus: "${latestSearch.query}" · ${creatives.length} ads indexed`
            : `${creatives.length} competitor ads indexed`
        }
        actions={
          <Button size="xs" variant="outline" onClick={() => navigate("/discover")}>
            New Search
          </Button>
        }
      />

      {/* Active Search Header */}
      {latestSearch ? (
        <div className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 rounded-full bg-accent" />
            <span className="text-xs font-mono text-text">
              Active Benchmark Query: <strong className="text-accent font-bold">"{latestSearch.query}"</strong>
            </span>
          </div>
          <span className="font-mono text-[11px] text-text-muted">
            Tracking {creatives.length} active ads
          </span>
        </div>
      ) : null}

      {loading ? (
        <div className="p-6">
          <SkeletonRows rows={8} />
        </div>
      ) : creatives.length === 0 ? (
        <div className="p-8">
          <EmptyState
            icon={Activity}
            title="No Performance Data Available"
            description="Run a search in the Discover tab to gather competitor ad run-times and performance signals."
            action={
              <Button size="sm" variant="primary" onClick={() => navigate("/discover")}>
                Start in Discover
              </Button>
            }
          />
        </div>
      ) : (
        <div className="p-6 space-y-6">
          
          {/* Top Aggregate KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            <div className="rounded border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="label-mono text-text-faint">Average Active Duration</span>
                <Clock className="h-4 w-4 text-accent" />
              </div>
              <p className="text-2xl font-mono font-bold text-text mt-2">
                {metrics.avgDays} <span className="text-sm font-normal text-text-muted">days</span>
              </p>
              <span className="text-[11px] text-text-muted mt-1 block">
                Average competitor test cycle
              </span>
            </div>

            <div className="rounded border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="label-mono text-text-faint">Evergreen Survivor Rate</span>
                <Award className="h-4 w-4 text-success" />
              </div>
              <p className="text-2xl font-mono font-bold text-success mt-2">
                {metrics.survivorRate}%
              </p>
              <span className="text-[11px] text-text-muted mt-1 block">
                {metrics.survivorCount} of {creatives.length} ads active &ge;14 days
              </span>
            </div>

            <div className="rounded border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="label-mono text-text-faint">Average Composite Score</span>
                <TrendingUp className="h-4 w-4 text-amber-400" />
              </div>
              <p className="text-2xl font-mono font-bold text-amber-400 mt-2">
                {metrics.avgScore} <span className="text-sm font-normal text-text-muted">/ 100</span>
              </p>
              <span className="text-[11px] text-text-muted mt-1 block">
                Hook & clarity benchmark
              </span>
            </div>

            <div className="rounded border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="label-mono text-text-faint">Format Distribution</span>
                <Layers className="h-4 w-4 text-info" />
              </div>
              <p className="text-2xl font-mono font-bold text-info mt-2">
                {metrics.videoCount} <span className="text-sm font-normal text-text-muted">videos / {creatives.length - metrics.videoCount} stills</span>
              </p>
              <span className="text-[11px] text-text-muted mt-1 block">
                {Math.round((metrics.videoCount / creatives.length) * 100)}% video share
              </span>
            </div>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <span className="label-mono text-text">Filter:</span>
              <div className="flex items-center rounded border border-border bg-surface p-0.5 text-xs">
                {["ALL", "video", "image"].map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => setFilterFormat(fmt)}
                    className={`rounded px-2.5 py-1 capitalize font-mono text-[11px] transition-colors ${
                      filterFormat === fmt
                        ? "bg-accent text-black font-semibold"
                        : "text-text-muted hover:text-text"
                    }`}
                  >
                    {fmt === "ALL" ? "All Formats" : fmt}
                  </button>
                ))}
              </div>

              <div className="flex items-center rounded border border-border bg-surface p-0.5 text-xs">
                {[0, 7, 14, 30].map((days) => (
                  <button
                    key={days}
                    type="button"
                    onClick={() => setMinDays(days)}
                    className={`rounded px-2.5 py-1 font-mono text-[11px] transition-colors ${
                      minDays === days
                        ? "bg-surface-3 text-text font-semibold"
                        : "text-text-muted hover:text-text"
                    }`}
                  >
                    {days === 0 ? "Any Duration" : `≥${days}d`}
                  </button>
                ))}
              </div>
            </div>

            <span className="font-mono text-xs text-text-muted">
              Showing {filteredCreatives.length} ads ranked by durability
            </span>
          </div>

          {/* Survivor Leaderboard Table */}
          <div className="rounded border border-border bg-surface overflow-hidden">
            <div className="border-b border-border bg-surface-2 px-4 py-2.5 flex items-center justify-between">
              <span className="label-mono text-text flex items-center gap-1.5">
                <BarChart3 className="h-3.5 w-3.5 text-accent" />
                Durability & Fatigue Leaderboard
              </span>
              <span className="text-[10px] font-mono text-text-faint">
                Long-running ads indicate winning ROAS & high budget scaling
              </span>
            </div>

            <div className="divide-y divide-border">
              {filteredCreatives.map((c, idx) => {
                const days = c.days_active || 1
                const isSurvivor = days >= 14
                const isEvergreen = days >= 30
                const isSaved = savedIds.has(c.id)

                return (
                  <div
                    key={c.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 hover:bg-surface-2 transition-colors"
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <span className="font-mono text-xs font-bold text-text-faint pt-1">
                        #{idx + 1}
                      </span>

                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-surface-2 border border-border text-text-muted">
                        {c.format === "video" ? (
                          <Play className="h-4 w-4 text-accent" />
                        ) : (
                          <ImageIcon className="h-4 w-4 text-text-muted" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-xs font-bold text-text">
                            {c.headline || c.brand_name || "Ad Creative"}
                          </p>

                          {isEvergreen ? (
                            <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-emerald-400 border border-emerald-500/20">
                              Evergreen Survivor
                            </span>
                          ) : isSurvivor ? (
                            <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-amber-400 border border-amber-500/20">
                              Scaling Phase
                            </span>
                          ) : (
                            <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[10px] font-mono text-text-faint border border-border">
                              Testing
                            </span>
                          )}
                        </div>

                        <p className="text-xs text-text-muted mt-1 line-clamp-1">
                          {c.body || "No copy text indexed"}
                        </p>

                        <div className="flex items-center gap-3 mt-1.5 font-mono text-[10px] text-text-faint">
                          <span className="capitalize">{c.platform}</span>
                          <span>·</span>
                          <span className="capitalize">{c.format}</span>
                          {c.cta && (
                            <>
                              <span>·</span>
                              <span className="text-text-muted">CTA: {c.cta}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Stats & Actions */}
                    <div className="flex items-center justify-between sm:justify-end gap-5 shrink-0 border-t sm:border-t-0 pt-2 sm:pt-0 border-border">
                      <div className="flex flex-col items-center sm:items-end">
                        <span className="font-mono text-sm font-bold text-success">
                          {days} days active
                        </span>
                        <span className="text-[10px] font-mono text-text-faint">
                          Durability index
                        </span>
                      </div>

                      <div className="flex flex-col items-center sm:items-end">
                        <span className="font-mono text-sm font-bold text-accent">
                          {c.scores?.composite ?? 88}
                        </span>
                        <span className="text-[10px] font-mono text-text-faint">
                          Composite score
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => handleToggleSave(c)}
                          title={isSaved ? "Saved in Swipe Files" : "Save to Swipe Files"}
                        >
                          <Bookmark className={`h-3.5 w-3.5 ${isSaved ? "fill-accent text-accent" : "text-text-faint"}`} />
                        </Button>

                        <Button
                          size="xs"
                          variant="primary"
                          onClick={() => handleRemix(c)}
                          className="flex items-center gap-1 font-medium text-[11px]"
                        >
                          <Sparkles className="h-3 w-3 text-black" />
                          Remix
                        </Button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default PerformancePage
