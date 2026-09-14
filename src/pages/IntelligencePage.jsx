import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States"
import { InfoTip } from "@/components/ui/InfoTip"
import { useLanguage } from "@/context/LanguageContext"
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
  BookOpen,
  Globe,
  Languages,
  Loader2
} from "lucide-react"
import { playbookService } from "@/services"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"

const COPY_LANGUAGES = [
  { id: "en", label: "English", flag: "🇺🇸" },
  { id: "es", label: "Spanish", flag: "🇪🇸" },
  { id: "zh", label: "Chinese", flag: "🇨🇳" },
  { id: "nl", label: "Dutch", flag: "🇳🇱" },
  { id: "ar", label: "Arabic", flag: "🇸🇦" },
]


export function IntelligencePage() {
  const navigate = useNavigate()
  const { latestSearch, searchHistory, activeCreative, selectActiveCreative, selectSearchSession } = useSearchContext()
  const { t } = useLanguage()
  
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
  const [analysisError, setAnalysisError] = useState(null)

  // Load creatives from latest search or fallback to recent DB creatives
  useEffect(() => {
    let isMounted = true
    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        if (latestSearch?.query) {
          // A completed search owns this tab. Zero hits must stay empty —
          // do not relabel leftover ads from another job as this query.
          const items = latestSearch.items || []
          setCreatives(items)
          setSelectedCreativeId(items[0]?.id || activeCreative?.id || null)
        } else {
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

  const [copyLang, setCopyLang] = useState("en")
  const [translations, setTranslations] = useState({})
  const [translatingCopy, setTranslatingCopy] = useState(false)
  const [showRawCopy, setShowRawCopy] = useState(false)

  // Auto-translate selected creative copy to English by default or user-selected language
  useEffect(() => {
    if (!selectedCreative?.body) return
    const cacheKey = `${selectedCreative.id}_${copyLang}`
    if (translations[cacheKey]) return

    let isMounted = true
    setTranslatingCopy(true)

    creativeService
      .translateCopy(selectedCreative.body, copyLang, true)
      .then((res) => {
        if (!isMounted) return
        setTranslations((prev) => ({ ...prev, [cacheKey]: res }))
      })
      .catch((err) => {
        console.warn("Copy translation failed:", err)
      })
      .finally(() => {
        if (isMounted) setTranslatingCopy(false)
      })

    return () => {
      isMounted = false
    }
  }, [selectedCreative?.id, selectedCreative?.body, copyLang])

  const currentTranslation = selectedCreative ? translations[`${selectedCreative.id}_${copyLang}`] : null
  const breakdown = currentTranslation?.breakdown

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
    setAnalysisError(null)
    try {
      const result = await analysisService.generateInsight(selectedCreativeId)
      setInsights((prev) => ({ ...prev, [selectedCreativeId]: result }))
    } catch (err) {
      // Honest failure: show the real reason, never a fabricated insight.
      setAnalysisError(err?.message || "Analysis is temporarily unavailable. Please try again.")
    } finally {
      setGeneratingInsight(false)
    }
  }

  async function handleGeneratePatterns() {
    setGeneratingPatterns(true)
    setAnalysisError(null)
    try {
      const res = await analysisService.generatePatterns()
      if (Array.isArray(res) && res.length > 0) {
        setPatterns(res)
      } else {
        const patRes = await creativeService.getPatterns()
        if (patRes?.items) setPatterns(patRes.items)
      }
    } catch (err) {
      setAnalysisError(err?.message || "Pattern extraction is temporarily unavailable. Please try again.")
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
    <div className="flex min-h-0 flex-1 flex-col">
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
              {generatingPatterns ? t("synthesizing") : `${t("synthesizePatterns")} (1.0 cr)`}
            </Button>
          </div>
        }
      />

      {/* Active Search / Context Banner */}
      {latestSearch ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface-2 px-4 py-2.5">
          <div className="flex items-center gap-3">
            <span className="flex h-2 w-2 rounded-full bg-accent animate-pulse" />
            <span className="text-xs font-mono text-text">
              Active Corpus: <strong className="text-accent font-bold">"{latestSearch.query}"</strong> · {creatives.length} ads indexed
            </span>

            {searchHistory.length > 1 && (
              <select
                value={latestSearch.query}
                onChange={(e) => {
                  const target = searchHistory.find((s) => s.query === e.target.value)
                  if (target) selectSearchSession(target)
                }}
                className="text-[11px] font-mono bg-surface border border-border rounded px-2 py-1 text-text focus:outline-none focus:border-accent"
              >
                {searchHistory.map((s) => (
                  <option key={s.query} value={s.query}>
                    Corpus: {s.query} ({s.total || s.items?.length || 0} ads)
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button size="xs" variant="ghost" onClick={() => navigate("/discover")}>
              {t("runNewSearch")}
            </Button>
            <Button size="xs" variant="outline" onClick={() => navigate("/create")}>
              {t("goToCreate")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-2 text-xs text-text-muted">
          <span>Tip: Run a search in <strong>Discover</strong> to extract competitive patterns from fresh ad library data.</span>
          <Button size="xs" variant="primary" onClick={() => navigate("/discover")}>
            {t("openDiscover")}
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
            title={t("noCorpusTitle")}
            description={t("noCorpusDesc")}
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
                          {t("family")}: {p.family || "Hook Formula"}
                        </span>
                      </div>
                      <div className="flex flex-col items-end shrink-0 font-mono text-[10px]">
                        <span className="flex items-center text-accent font-bold">
                          +{typeof p.lift_index === "number" ? p.lift_index.toFixed(1) : "2.4"}x Lift
                          <InfoTip
                            text="How much more often this pattern appears in strong-performing ads compared to average ones."
                            label="What does Lift mean?"
                          />
                        </span>
                        <span className="flex items-center text-text-faint">
                          {p.prevalence ? `${(p.prevalence * 100).toFixed(0)}% prev` : "High"}
                          <InfoTip
                            text="The share of ads in this search that use this pattern."
                            label="What does prevalence mean?"
                          />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded border border-dashed border-border p-3 text-center text-xs text-text-muted">
                  {t("noPatternsYetDesc")}
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

                {/* Creative Copy Teardown & Multilingual Translation */}
                <div className="rounded border border-border bg-surface p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
                    <span className="label-mono text-text flex items-center gap-1.5 font-bold">
                      <Target className="h-3.5 w-3.5 text-accent" />
                      Ad Copy & Conversion Anatomy
                    </span>

                    {/* Language Selector / Dragger Bar */}
                    <div className="flex flex-wrap items-center gap-1 bg-surface-2 p-1 rounded-md border border-border">
                      <Languages className="h-3 w-3 text-text-faint ml-1.5 mr-1" />
                      {COPY_LANGUAGES.map((lang) => {
                        const isActive = copyLang === lang.id
                        return (
                          <button
                            key={lang.id}
                            type="button"
                            onClick={() => setCopyLang(lang.id)}
                            className={`px-2.5 py-1 text-[11px] font-mono rounded transition-all flex items-center gap-1 ${
                              isActive
                                ? "bg-accent text-bg font-bold shadow-sm"
                                : "text-text-muted hover:text-text hover:bg-surface-3"
                            }`}
                          >
                            <span>{lang.flag}</span>
                            <span>{lang.label}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Status / Loading indicator */}
                  {translatingCopy && (
                    <div className="flex items-center gap-2 py-2 px-3 text-xs text-accent bg-accent/10 border border-accent/20 rounded font-mono animate-pulse">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Translating copy into {COPY_LANGUAGES.find((l) => l.id === copyLang)?.label} & extracting structure…</span>
                    </div>
                  )}

                  {/* Structured Breakdown: Hook, Problem, Solution, CTA */}
                  {breakdown ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {/* Hook */}
                      <div className="rounded bg-surface-2 p-3 border border-border/60 space-y-1">
                        <div className="flex items-center gap-1.5 text-amber-400 font-mono text-[10px] uppercase font-bold tracking-wider">
                          <Zap className="h-3 w-3" />
                          <span>1. Hook / Pattern Interrupt</span>
                        </div>
                        <p className="text-xs text-text leading-relaxed font-sans">
                          {breakdown.hook || "—"}
                        </p>
                      </div>

                      {/* Problem & Agitation */}
                      <div className="rounded bg-surface-2 p-3 border border-border/60 space-y-1">
                        <div className="flex items-center gap-1.5 text-rose-400 font-mono text-[10px] uppercase font-bold tracking-wider">
                          <Flame className="h-3 w-3" />
                          <span>2. Problem & Agitation</span>
                        </div>
                        <p className="text-xs text-text leading-relaxed font-sans">
                          {breakdown.problem || "—"}
                        </p>
                      </div>

                      {/* Solution / Offer */}
                      <div className="rounded bg-surface-2 p-3 border border-border/60 space-y-1">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[10px] uppercase font-bold tracking-wider">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>3. Transformation & Solution</span>
                        </div>
                        <p className="text-xs text-text leading-relaxed font-sans">
                          {breakdown.solution || "—"}
                        </p>
                      </div>

                      {/* Call to Action */}
                      <div className="rounded bg-surface-2 p-3 border border-border/60 space-y-1">
                        <div className="flex items-center gap-1.5 text-cyan-400 font-mono text-[10px] uppercase font-bold tracking-wider">
                          <ArrowRight className="h-3 w-3" />
                          <span>4. Direct Call To Action</span>
                        </div>
                        <p className="text-xs text-text font-bold font-mono tracking-wide">
                          {breakdown.cta || selectedCreative?.cta || "—"}
                        </p>
                      </div>
                    </div>
                  ) : null}

                  {/* Clean Formatted Body Text */}
                  {selectedCreative.body && (
                    <div className="rounded bg-surface-2 p-3.5 text-xs text-text leading-relaxed border border-border/50 space-y-2">
                      <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
                        <span className="font-mono text-[10px] text-text-faint uppercase tracking-wider flex items-center gap-1">
                          <Globe className="h-3 w-3 text-accent" />
                          {showRawCopy
                            ? "Original Raw Copy (Verbatim)"
                            : `Translated Body Text (${COPY_LANGUAGES.find((l) => l.id === copyLang)?.label})`}
                        </span>
                        <button
                          type="button"
                          onClick={() => setShowRawCopy((v) => !v)}
                          className="font-mono text-[10px] text-text-muted hover:text-accent underline cursor-pointer"
                        >
                          {showRawCopy ? "Show Translated" : "View Original Copy"}
                        </button>
                      </div>
                      <p className="whitespace-pre-line text-xs font-sans text-text leading-relaxed">
                        {showRawCopy
                          ? selectedCreative.body
                          : currentTranslation?.translated_text || selectedCreative.body}
                      </p>
                    </div>
                  )}

                  {selectedCreative.cta && (
                    <div className="flex items-center justify-between rounded bg-surface-2 px-3 py-2 text-xs border border-border/50">
                      <span className="text-text-muted font-mono text-[11px]">Primary Button / CTA</span>
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
                        {generatingInsight ? t("analyzingTeardown") : t("generateTeardown")}
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
                  ) : analysisError ? (
                    <div className="rounded border border-warning/40 bg-warning/5 p-4 text-left space-y-2">
                      <p className="flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase text-warning">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        {t("analysisUnavailable")}
                      </p>
                      <p className="text-xs leading-relaxed text-text-muted">{analysisError}</p>
                      <div>
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={handleGenerateInsight}
                          disabled={generatingInsight}
                          className="font-mono text-[11px]"
                        >
                          {t("tryAgain")}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded border border-dashed border-border p-6 text-center text-xs text-text-muted space-y-2">
                      <p>{t("noTeardownYet")}</p>
                      <p className="text-[11px] text-text-faint">
                        {t("noTeardownYetDesc")}
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
