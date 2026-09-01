import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States"
import { useSearchContext } from "@/context/SearchContext"
import { creativeService, analysisService } from "@/services"
import {
  Network,
  Sparkles,
  Zap,
  Target,
  Flame,
  Brain,
  Lightbulb,
  ArrowRight,
  TrendingUp,
  Clock,
  Layers,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Play,
  Image as ImageIcon,
  Share2,
  BookOpen
} from "lucide-react"
import { playbookService } from "@/services"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"

export function IntelligencePage() {
  const navigate = useNavigate()
  const { latestSearch, searchHistory, activeCreative, selectActiveCreative } = useSearchContext()
  
  const [creatives, setCreatives] = useState([])
  const [selectedCreativeId, setSelectedCreativeId] = useState(null)
  const [insights, setInsights] = useState({})
  const [patterns, setPatterns] = useState([])
  const [loading, setLoading] = useState(true)
  const [generatingInsight, setGeneratingInsight] = useState(false)
  const [generatingPatterns, setGeneratingPatterns] = useState(false)
  const [compilingPlaybook, setCompilingPlaybook] = useState(false)
  const [isSupportOpen, setIsSupportOpen] = useState(false)
  const [error, setError] = useState(null)

  // Load creatives from latest search or fallback to recent DB creatives
  useEffect(() => {
    let isMounted = true
    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        if (latestSearch?.items && latestSearch.items.length > 0) {
          setCreatives(latestSearch.items)
          const firstId = activeCreative?.id || latestSearch.items[0]?.id
          setSelectedCreativeId(firstId)
        } else {
          // Fetch from backend API
          const res = await creativeService.getCreatives({ page: 1, page_size: 20 })
          if (isMounted) {
            const items = res?.items || []
            setCreatives(items)
            if (items.length > 0) {
              setSelectedCreativeId(activeCreative?.id || items[0]?.id)
            }
          }
        }

        // Fetch patterns
        try {
          const patRes = await creativeService.getPatterns()
          if (isMounted && patRes?.items) {
            setPatterns(patRes.items)
          }
        } catch (e) {
          console.warn("Could not fetch pattern list", e)
        }
      } catch (err) {
        if (isMounted) setError(err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    loadData()
    return () => { isMounted = false }
  }, [latestSearch, activeCreative?.id])

  // Load or generate insight for selected creative
  const selectedCreative = creatives.find((c) => c.id === selectedCreativeId)

  useEffect(() => {
    if (!selectedCreativeId) return
    if (insights[selectedCreativeId]) return

    let isMounted = true
    analysisService.getInsight(selectedCreativeId)
      .then((res) => {
        if (!isMounted) return
        const insightItem = res?.items?.[0] || res
        if (insightItem && (insightItem.script_teardown || insightItem.emotional_resonance)) {
          setInsights((prev) => ({ ...prev, [selectedCreativeId]: insightItem }))
        }
      })
      .catch(() => {})

    return () => { isMounted = false }
  }, [selectedCreativeId, insights])

  async function handleGenerateInsight() {
    if (!selectedCreativeId) return
    setGeneratingInsight(true)
    try {
      const result = await analysisService.generateInsight(selectedCreativeId)
      setInsights((prev) => ({ ...prev, [selectedCreativeId]: result }))
    } catch (err) {
      alert(`AI Insight generation failed: ${err.message || err}`)
    } finally {
      setGeneratingInsight(false)
    }
  }

  async function handleGeneratePatterns() {
    setGeneratingPatterns(true)
    try {
      const res = await analysisService.generatePatterns()
      if (Array.isArray(res) && res.length > 0) {
        setPatterns(res)
      } else {
        const patRes = await creativeService.getPatterns()
        if (patRes?.items) setPatterns(patRes.items)
      }
    } catch (err) {
      alert(`Pattern extraction failed: ${err.message || err}`)
    } finally {
      setGeneratingPatterns(false)
    }
  }

  async function handleCompilePlaybook() {
    setCompilingPlaybook(true)
    try {
      const brand = latestSearch?.query || (creatives[0]?.brand_name) || "brand"
      const res = await playbookService.compilePlaybook({
        brand_name: brand,
        query: brand,
        job_id: latestSearch?.job_id || null
      })
      if (res?.public_id) {
        navigate(`/playbook/${res.public_id}`)
      }
    } catch (err) {
      alert(`Playbook compilation failed: ${err.message || err}`)
    } finally {
      setCompilingPlaybook(false)
    }
  }

  function handleSendToCreate(creative) {
    if (creative) {
      selectActiveCreative(creative)
      navigate(`/create?sourceId=${creative.id}`)
    }
  }

  const currentInsight = selectedCreativeId ? insights[selectedCreativeId] : null

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar
        trail={["Helix", "Intelligence", "Pattern Extraction"]}
        meta={
          latestSearch
            ? `Active search: "${latestSearch.query}" (${creatives.length} creatives)`
            : `${creatives.length} creatives indexed`
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="outline"
              onClick={() => setIsSupportOpen(true)}
              className="text-xs text-text-muted"
            >
              Report Issue
            </Button>
            <Button
              size="xs"
              variant="secondary"
              onClick={handleCompilePlaybook}
              disabled={compilingPlaybook || creatives.length === 0}
              className="flex items-center gap-1.5"
            >
              <BookOpen className="h-3 w-3 text-emerald-400" />
              {compilingPlaybook ? "Compiling..." : "Compile Playbook (Free)"}
            </Button>
            <Button
              size="xs"
              variant="primary"
              onClick={handleGeneratePatterns}
              disabled={generatingPatterns || creatives.length === 0}
              className="flex items-center gap-1.5"
            >
              <Sparkles className="h-3 w-3" />
              {generatingPatterns ? "Synthesizing Patterns..." : "Synthesize Patterns (1.0 cr)"}
            </Button>
          </div>
        }
      />

      {/* Active Search / Context Banner */}
      {latestSearch ? (
        <div className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 rounded-full bg-accent animate-pulse" />
            <span className="text-xs font-mono text-text">
              CORPUS: <strong className="text-accent font-bold">"{latestSearch.query}"</strong> · {latestSearch.total} records found
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button size="xs" variant="ghost" onClick={() => navigate("/discover")}>
              Run New Search
            </Button>
            <Button size="xs" variant="outline" onClick={() => navigate("/create")}>
              Go to Create Studio →
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-2 text-xs text-text-muted">
          <span>Tip: Run a search in <strong>Discover</strong> to extract competitive patterns from fresh ad library data.</span>
          <Button size="xs" variant="primary" onClick={() => navigate("/discover")}>
            Open Discover
          </Button>
        </div>
      )}

      {loading ? (
        <div className="p-6">
          <SkeletonRows rows={8} />
        </div>
      ) : creatives.length === 0 ? (
        <div className="p-8">
          <EmptyState
            icon={Network}
            title="No Creative Corpus Available"
            description="Run a discovery query in the Discover tab to populate the corpus with competitor ads, or generate a sample analysis."
            action={
              <Button size="sm" variant="primary" onClick={() => navigate("/discover")}>
                Go to Discover
              </Button>
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 flex-1 min-h-0 border-b border-border">
          
          {/* Left Panel: Discovered Ads Selector & Pattern Matrix */}
          <div className="lg:col-span-5 border-r border-border flex flex-col bg-surface overflow-y-auto">
            
            {/* Pattern Packs Section */}
            <div className="border-b border-border p-3.5 bg-surface-2">
              <div className="flex items-center justify-between mb-2">
                <span className="label-mono flex items-center gap-1.5 text-text">
                  <Brain className="h-3.5 w-3.5 text-accent" />
                  Extracted Pattern Packs
                </span>
                <span className="text-[10px] font-mono text-text-faint">
                  {patterns.length > 0 ? `${patterns.length} formulas` : "Synthesizing..."}
                </span>
              </div>

              {patterns.length > 0 ? (
                <div className="grid grid-cols-1 gap-1.5">
                  {patterns.slice(0, 4).map((p, idx) => (
                    <div
                      key={p.id || idx}
                      className="flex items-center justify-between rounded border border-border bg-surface p-2 text-xs transition-colors hover:border-accent/50"
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center gap-1.5 font-medium text-text">
                          <Zap className="h-3 w-3 text-accent shrink-0" />
                          <span className="truncate">{p.label}</span>
                        </div>
                        <span className="text-[10px] font-mono text-text-muted capitalize">
                          Family: {p.family || "Hook Formula"}
                        </span>
                      </div>
                      <div className="flex flex-col items-end shrink-0 font-mono text-[10px]">
                        <span className="text-accent font-bold">
                          +{typeof p.lift_index === "number" ? p.lift_index.toFixed(1) : "2.4"}x Lift
                        </span>
                        <span className="text-text-faint">
                          {p.prevalence ? `${(p.prevalence * 100).toFixed(0)}% prev` : "High"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded border border-dashed border-border p-3 text-center text-xs text-text-muted">
                  Click "Synthesize Patterns" to mine recurring hook formulas across this corpus.
                </div>
              )}
            </div>

            {/* Creatives List */}
            <div className="p-3 bg-surface border-b border-border flex items-center justify-between">
              <span className="label-mono text-text">Corpus Creatives ({creatives.length})</span>
              <span className="text-[10px] font-mono text-text-faint">Click to inspect</span>
            </div>

            <div className="divide-y divide-border overflow-y-auto flex-1">
              {creatives.map((c) => {
                const isSelected = c.id === selectedCreativeId
                const hasInsight = Boolean(insights[c.id])
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      setSelectedCreativeId(c.id)
                      selectActiveCreative(c)
                    }}
                    className={`w-full text-left p-3 transition-colors flex items-start gap-3 ${
                      isSelected
                        ? "bg-surface-3 border-l-2 border-accent"
                        : "hover:bg-surface-2"
                    }`}
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-surface-2 border border-border text-text-muted">
                      {c.format === "video" ? (
                        <Play className="h-4 w-4 text-accent" />
                      ) : (
                        <ImageIcon className="h-4 w-4 text-text-muted" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <p className="truncate text-xs font-semibold text-text">
                          {c.headline || c.brand_name || "Ad Creative"}
                        </p>
                        {hasInsight && (
                          <span className="flex items-center gap-1 text-[10px] font-mono text-accent">
                            <Sparkles className="h-2.5 w-2.5" /> Analyzed
                          </span>
                        )}
                      </div>
                      <p className="truncate text-[11px] text-text-muted mt-0.5 line-clamp-1">
                        {c.body || "No body text available"}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5 font-mono text-[10px] text-text-faint">
                        <span className="capitalize">{c.platform || "Meta"}</span>
                        <span>·</span>
                        <span>{c.days_active || 1}d active</span>
                        {c.scores?.composite && (
                          <>
                            <span>·</span>
                            <span className="text-accent">Score: {c.scores.composite}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Right Panel: Deep LLM Insight & Script Breakdown */}
          <div className="lg:col-span-7 flex flex-col bg-surface-2 p-5 overflow-y-auto">
            {selectedCreative ? (
              <div className="space-y-5">
                
                {/* Header & Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
                  <div>
                    <span className="label-mono text-accent">Deep Creative Breakdown</span>
                    <h3 className="text-base font-bold text-text mt-0.5">
                      {selectedCreative.headline || "Selected Creative"}
                    </h3>
                    <p className="text-xs text-text-muted font-mono">
                      ID: {selectedCreative.id.slice(0, 12)}... · {selectedCreative.platform} · {selectedCreative.format}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleSendToCreate(selectedCreative)}
                      className="flex items-center gap-1.5 font-medium"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-black" />
                      Remix in Create Studio
                    </Button>
                  </div>
                </div>

                {/* Score Cards Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  <div className="rounded border border-border bg-surface p-3 text-center">
                    <span className="label-mono text-text-faint">Hook Score</span>
                    <p className="text-xl font-mono font-bold text-accent mt-1">
                      {selectedCreative.scores?.hook ? Math.round(selectedCreative.scores.hook) : "—"}
                    </p>
                    <span className="text-[10px] text-text-muted">First 3s retention</span>
                  </div>

                  <div className="rounded border border-border bg-surface p-3 text-center">
                    <span className="label-mono text-text-faint">Clarity</span>
                    <p className="text-xl font-mono font-bold text-text mt-1">
                      {selectedCreative.scores?.clarity ? Math.round(selectedCreative.scores.clarity) : "—"}
                    </p>
                    <span className="text-[10px] text-text-muted">Value prop speed</span>
                  </div>

                  <div className="rounded border border-border bg-surface p-3 text-center">
                    <span className="label-mono text-text-faint">Lifespan</span>
                    <p className="text-xl font-mono font-bold text-success mt-1">
                      {selectedCreative.days_active || 1}d
                    </p>
                    <span className="text-[10px] text-text-muted">Surviving fatigue</span>
                  </div>

                  <div className="rounded border border-border bg-surface p-3 text-center">
                    <span className="label-mono text-text-faint">Composite</span>
                    <p className="text-xl font-mono font-bold text-amber-400 mt-1">
                      {selectedCreative.scores?.composite ? Math.round(selectedCreative.scores.composite) : "—"}
                    </p>
                    <span className="text-[10px] text-text-muted">Overall potency</span>
                  </div>
                </div>

                {/* Creative Copy Teardown */}
                <div className="rounded border border-border bg-surface p-4 space-y-3">
                  <span className="label-mono text-text flex items-center gap-1.5">
                    <Target className="h-3.5 w-3.5 text-accent" />
                    Ad Copy & Call to Action
                  </span>
                  
                  {selectedCreative.body && (
                    <div className="rounded bg-surface-2 p-3 text-xs text-text leading-relaxed border border-border/50">
                      <p className="font-mono text-[10px] text-text-faint uppercase mb-1">Primary Body Text</p>
                      "{selectedCreative.body}"
                    </div>
                  )}

                  {selectedCreative.cta && (
                    <div className="flex items-center justify-between rounded bg-surface-2 px-3 py-2 text-xs border border-border/50">
                      <span className="text-text-muted font-mono text-[11px]">Call To Action</span>
                      <span className="font-mono font-semibold text-accent uppercase tracking-wider">
                        {selectedCreative.cta}
                      </span>
                    </div>
                  )}
                </div>

                {/* LLM Insight Section */}
                <div className="rounded border border-border bg-surface p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="label-mono text-text flex items-center gap-1.5">
                      <Brain className="h-3.5 w-3.5 text-accent" />
                      LLM Strategic Intelligence
                    </span>
                    
                    {!currentInsight && (
                      <Button
                        size="xs"
                        variant="primary"
                        onClick={handleGenerateInsight}
                        disabled={generatingInsight}
                        className="flex items-center gap-1 font-mono text-[11px]"
                      >
                        <Sparkles className="h-3 w-3" />
                        {generatingInsight ? "Analyzing (Pattern Engine)..." : "Generate Deep Teardown (1.0 cr)"}
                      </Button>
                    )}
                  </div>

                  {currentInsight ? (
                    <div className="space-y-3 text-xs">
                      {currentInsight.emotional_resonance && (
                        <div className="rounded bg-surface-2 p-3 border border-border/50">
                          <p className="font-mono text-[11px] font-bold text-accent uppercase mb-1 flex items-center gap-1.5">
                            <Flame className="h-3.5 w-3.5 text-amber-400" />
                            Emotional Trigger & Resonance
                          </p>
                          <p className="text-text leading-relaxed">
                            {currentInsight.emotional_resonance}
                          </p>
                        </div>
                      )}

                      {currentInsight.script_teardown && (
                        <div className="rounded bg-surface-2 p-3 border border-border/50">
                          <p className="font-mono text-[11px] font-bold text-accent uppercase mb-1 flex items-center gap-1.5">
                            <Layers className="h-3.5 w-3.5 text-info" />
                            Beat-by-Beat Script Teardown
                          </p>
                          <div className="text-text whitespace-pre-line leading-relaxed font-sans">
                            {typeof currentInsight.script_teardown === "string" 
                              ? currentInsight.script_teardown 
                              : JSON.stringify(currentInsight.script_teardown, null, 2)}
                          </div>
                        </div>
                      )}

                      {currentInsight.fatigue_prediction && (
                        <div className="rounded bg-surface-2 p-3 border border-border/50">
                          <p className="font-mono text-[11px] font-bold text-warning uppercase mb-1 flex items-center gap-1.5">
                            <Clock className="h-3.5 w-3.5 text-warning" />
                            Fatigue & Durability Forecast
                          </p>
                          <p className="text-text leading-relaxed">
                            {currentInsight.fatigue_prediction}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded border border-dashed border-border p-6 text-center text-xs text-text-muted space-y-2">
                      <p>No LLM strategic teardown generated for this creative yet.</p>
                      <p className="text-[11px] text-text-faint">
                        Click "Generate Deep Teardown" to run full script analysis, emotional trigger mapping, and audience fatigue prediction.
                      </p>
                    </div>
                  )}
                </div>

              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-text-muted">
                Select a creative from the left panel to inspect intelligence.
              </div>
            )}
          </div>

        </div>
      )}

      <SupportFeedbackModal
        isOpen={isSupportOpen}
        onClose={() => setIsSupportOpen(false)}
        initialContext={{ page: "Intelligence & Patterns", tag: "intelligence" }}
      />
    </div>
  )
}

export default IntelligencePage
