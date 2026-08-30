import { useState, useEffect } from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import {
  PenLine,
  Play,
  Image as ImageIcon,
  CheckCircle,
  AlertCircle,
  Loader,
  Sparkles,
  Video,
  Film,
  Wand2,
  ChevronDown,
  Layers,
  Zap,
  ArrowRight
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { creativeService } from "@/services"
import { useMediaGenerate, PHASE } from "@/hooks/useMediaGenerate"
import { useSearchContext } from "@/context/SearchContext"

const CREATIVE_MODES = {
  image: [
    { id: "premium_ad", label: "Premium Ad (3.0 cr)", desc: "Soul 2 photorealistic commercial still (Default)" },
    { id: "quick_concept", label: "Quick Concept (3.0 cr)", desc: "Popcorn fast ideation & variations" },
    { id: "cinematic_ad", label: "Cinematic Ad (3.0 cr)", desc: "Soul Cinema luxury & dramatic lighting" },
    { id: "storyboard", label: "Storyboard (3.0 cr)", desc: "Popcorn multi-angle narrative sequence" },
  ],
  video: [
    { id: "quick_video", label: "Quick Video (8.0 cr)", desc: "DoP Turbo fast motion for social testing" },
    { id: "premium_video", label: "Premium Video (8.0 cr)", desc: "DoP Standard high-fidelity commercial" },
    { id: "before_after", label: "Before → After (8.0 cr)", desc: "DoP FLF transition between two states", requiresFrames: true },
    { id: "controlled_video", label: "Controlled Video (8.0 cr)", desc: "DoP Standard Keyframed brand video", requiresFrames: true },
  ]
}

const ASPECT_RATIOS = [
  { id: "1:1", label: "1:1 Square (Feed / Instagram)" },
  { id: "9:16", label: "9:16 Vertical (Stories / TikTok / Reels)" },
  { id: "16:9", label: "16:9 Landscape (YouTube / Desktop)" },
]

export function CreatePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const sourceId = searchParams.get("sourceId")
  const navigate = useNavigate()
  
  const { latestSearch, activeCreative, selectActiveCreative } = useSearchContext()
  
  const [sourceCreative, setSourceCreative] = useState(null)
  const [activeCategory, setActiveCategory] = useState("image")
  const [selectedMode, setSelectedMode] = useState("premium_ad")
  const [aspectRatio, setAspectRatio] = useState("1:1")
  const [brief, setBrief] = useState("")
  const [startImageUrl, setStartImageUrl] = useState("")
  const [endImageUrl, setEndImageUrl] = useState("")
  const [showAdPicker, setShowAdPicker] = useState(false)
  
  const { phase, job, result, error, submit, cancel, isBusy } = useMediaGenerate()

  // Load source creative if sourceId is in URL
  useEffect(() => {
    if (sourceId) {
      creativeService.getCreativeById(sourceId).then((creative) => {
        if (creative) {
          applyCreativeToBrief(creative)
        }
      }).catch(err => {
        console.error("Failed to load source creative", err)
      })
    } else if (activeCreative && !sourceCreative) {
      applyCreativeToBrief(activeCreative)
    }
  }, [sourceId, activeCreative])

  function applyCreativeToBrief(creative) {
    setSourceCreative(creative)
    const headline = creative.headline ? `Headline: "${creative.headline}"` : ""
    const hook = creative.scores?.hook ? `[Hook score: ${creative.scores.hook}]` : ""
    const cta = creative.cta ? `Call-to-action: "${creative.cta}"` : ""
    setBrief(
      `Editorial commercial ad still remixing competitor pattern.\n${headline} ${hook}\n${cta}\nSetting: modern minimalist studio, bold dramatic side lighting, high contrast, clean background, 35mm photography, 8k commercial quality, no watermarks.`
    )
  }

  const handleCategoryChange = (category) => {
    setActiveCategory(category)
    if (category === "image") {
      setSelectedMode("premium_ad")
      setAspectRatio("1:1")
    } else {
      setSelectedMode("quick_video")
      setAspectRatio("9:16")
    }
  }

  const handleGenerate = () => {
    if (!brief.trim()) return
    
    const params = {
      mode: selectedMode,
      aspect_ratio: aspectRatio,
      kind: activeCategory,
      source_creative_id: sourceCreative?.id || sourceId
    }

    if (startImageUrl.trim()) params.start_image_url = startImageUrl.trim()
    if (endImageUrl.trim()) params.end_image_url = endImageUrl.trim()

    submit({
      prompt: brief,
      provider: "higgsfield",
      mode: selectedMode,
      parameters: params
    })
  }

  const isModeRequiringFrames = selectedMode === "before_after" || selectedMode === "controlled_video"

  let displayUrl = null
  let isVideo = false
  if (result) {
    if (result.type === "video" && result.video?.url) {
      displayUrl = result.video.url
      isVideo = true
    } else if (result.type === "image" && result.image?.url) {
      displayUrl = result.image.url
    } else if (result.result_url) {
      displayUrl = result.result_url
      isVideo = displayUrl.endsWith(".mp4")
    } else if (result.images && result.images.length > 0) {
      displayUrl = result.images[0].url
    }
  }

  const discoveredItems = latestSearch?.items || []

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar
        trail={["Helix", "Create", "Remix Studio"]}
        meta={activeCategory === "video" ? "Higgsfield DoP (8.0 cr)" : "Higgsfield Soul v2 (3.0 cr)"}
        actions={
          latestSearch ? (
            <Button size="xs" variant="ghost" onClick={() => navigate("/discover")}>
              From Search: "{latestSearch.query}" ({latestSearch.total} ads)
            </Button>
          ) : null
        }
      />

      <div className="flex-1 p-6 max-w-5xl mx-auto w-full">
        <div className="flex flex-col gap-6">

          {/* Quick Discovered Ads Selector Bar */}
          {discoveredItems.length > 0 && (
            <div className="rounded-lg border border-border bg-surface-2 p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-accent" />
                  <span className="text-xs font-mono font-semibold text-text">
                    Remix from Discovered Ads ("{latestSearch.query}")
                  </span>
                  <span className="text-[11px] font-mono text-text-muted">
                    ({discoveredItems.length} available)
                  </span>
                </div>
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => setShowAdPicker((v) => !v)}
                  className="flex items-center gap-1 text-[11px]"
                >
                  {showAdPicker ? "Hide Ads List" : "Pick Competitor Ad to Remix"}
                  <ChevronDown className={`h-3 w-3 transition-transform ${showAdPicker ? "rotate-180" : ""}`} />
                </Button>
              </div>

              {showAdPicker && (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 mt-3 pt-3 border-t border-border">
                  {discoveredItems.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => {
                        applyCreativeToBrief(c)
                        selectActiveCreative(c)
                        setShowAdPicker(false)
                      }}
                      className="flex items-start gap-2 rounded border border-border bg-surface p-2 text-left hover:border-accent transition-colors"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-surface-2 text-text-muted">
                        {c.format === "video" ? <Play className="h-3 w-3 text-accent" /> : <ImageIcon className="h-3 w-3 text-text-muted" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-text">{c.headline || c.brand_name || "Ad Creative"}</p>
                        <span className="text-[10px] font-mono text-text-muted">{c.days_active || 1}d active · {c.platform}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Form Section */}
            <div className="lg:col-span-7 flex flex-col gap-5">
              
              {/* Category Selection */}
              <div className="flex rounded-lg border border-border bg-surface p-1">
                <button
                  type="button"
                  onClick={() => handleCategoryChange("image")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-semibold rounded-md transition-colors ${
                    activeCategory === "image"
                      ? "bg-surface-3 text-text shadow-sm border border-border"
                      : "text-text-muted hover:text-text"
                  }`}
                >
                  <ImageIcon className="h-4 w-4 text-accent" />
                  Image Still (3.0 cr)
                </button>
                <button
                  type="button"
                  onClick={() => handleCategoryChange("video")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-semibold rounded-md transition-colors ${
                    activeCategory === "video"
                      ? "bg-surface-3 text-text shadow-sm border border-border"
                      : "text-text-muted hover:text-text"
                  }`}
                >
                  <Video className="h-4 w-4 text-accent" />
                  Video Motion (8.0 cr)
                </button>
              </div>

              {/* Mode Selection */}
              <div className="flex flex-col gap-2">
                <label className="label-mono text-text">Creative Mode</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {CREATIVE_MODES[activeCategory].map((mode) => (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setSelectedMode(mode.id)}
                      className={`flex flex-col text-left p-3 rounded-lg border transition-all ${
                        selectedMode === mode.id
                          ? "border-accent bg-accent/5 text-text ring-1 ring-accent"
                          : "border-border bg-surface text-text-muted hover:border-border-strong hover:text-text"
                      }`}
                    >
                      <span className="text-xs font-bold text-text">{mode.label}</span>
                      <span className="text-[11px] text-text-muted mt-1 leading-relaxed">{mode.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Aspect Ratio Selection */}
              <div className="flex flex-col gap-2">
                <label className="label-mono text-text">Aspect Ratio</label>
                <div className="flex flex-wrap gap-2">
                  {ASPECT_RATIOS.map((ratio) => (
                    <button
                      key={ratio.id}
                      type="button"
                      onClick={() => setAspectRatio(ratio.id)}
                      className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                        aspectRatio === ratio.id
                          ? "border-accent bg-accent/10 text-accent font-semibold"
                          : "border-border bg-surface text-text-muted hover:text-text"
                      }`}
                    >
                      {ratio.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Keyframe Reference Inputs */}
              {isModeRequiringFrames && (
                <div className="flex flex-col gap-3 p-4 rounded-lg border border-accent/30 bg-accent/5">
                  <div className="flex items-center gap-2 text-xs font-bold text-accent">
                    <Film className="h-4 w-4" />
                    Keyframe References (First & Last Frame)
                  </div>
                  <div className="flex flex-col gap-2">
                    <input
                      type="url"
                      placeholder="Start Image URL (e.g. initial problem state)"
                      value={startImageUrl}
                      onChange={(e) => setStartImageUrl(e.target.value)}
                      className="w-full text-xs rounded border border-border bg-bg p-2.5 text-text placeholder-text-faint focus:border-accent focus:outline-none font-mono"
                    />
                    <input
                      type="url"
                      placeholder="End Image URL (e.g. final solved state)"
                      value={endImageUrl}
                      onChange={(e) => setEndImageUrl(e.target.value)}
                      className="w-full text-xs rounded border border-border bg-bg p-2.5 text-text placeholder-text-faint focus:border-accent focus:outline-none font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Active Source Creative Card */}
              {sourceCreative && (
                <div className="flex items-center justify-between border border-accent/40 bg-surface-2 p-3 rounded-lg">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center bg-bg rounded border border-border">
                      {sourceCreative.format === "video" ? (
                        <Play className="h-4 w-4 text-accent" />
                      ) : (
                        <ImageIcon className="h-4 w-4 text-text-muted" />
                      )}
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate text-xs font-bold text-text">
                        Remixing: {sourceCreative.headline || "Competitor Ad"}
                      </span>
                      <span className="truncate text-[11px] text-text-muted font-mono">
                        {sourceCreative.platform} · {sourceCreative.days_active || 1}d active
                      </span>
                    </div>
                  </div>

                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => {
                      setSourceCreative(null)
                      setSearchParams({})
                    }}
                    className="text-[11px] text-text-faint"
                  >
                    Clear Source
                  </Button>
                </div>
              )}

              {/* Prompt Brief Section */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="label-mono text-text">Generation Prompt / Creative Brief</label>
                  <span className="text-[10px] font-mono text-text-faint">
                    {brief.length} characters
                  </span>
                </div>
                <textarea
                  rows={5}
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder="Describe the visual composition, lighting, camera angle, subject, and scene..."
                  className="w-full text-xs rounded-lg border border-border bg-surface p-3.5 text-text placeholder-text-faint focus:border-accent focus:outline-none font-sans leading-relaxed"
                />
              </div>

              {/* Submit Button */}
              <Button
                size="md"
                variant="primary"
                onClick={handleGenerate}
                disabled={isBusy || !brief.trim()}
                className="w-full flex items-center justify-center gap-2 text-sm font-bold shadow-lg"
              >
                {isBusy ? (
                  <>
                    <Loader className="h-4 w-4 animate-spin text-black" />
                    Generating Media with Higgsfield...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 text-black" />
                    Generate with Higgsfield ({activeCategory === "video" ? "8.0 cr" : "3.0 cr"})
                  </>
                )}
              </Button>
            </div>

            {/* Preview Output Panel */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              <label className="label-mono text-text">Live Output</label>
              
              <div className="flex-1 min-h-[360px] rounded-lg border border-border bg-surface p-4 flex flex-col items-center justify-center relative overflow-hidden">
                {isBusy ? (
                  <div className="flex flex-col items-center gap-3 text-center">
                    <div className="relative">
                      <div className="h-12 w-12 rounded-full border-2 border-accent/20 border-t-accent animate-spin" />
                      <Sparkles className="h-5 w-5 text-accent absolute inset-0 m-auto animate-pulse" />
                    </div>
                    <span className="text-xs font-semibold text-text">Higgsfield AI Processing</span>
                    <span className="text-[11px] font-mono text-text-muted">
                      {job?.status ? `Status: ${job.status}` : "Dispatching job to Higgsfield..."}
                    </span>
                  </div>
                ) : error ? (
                  <div className="flex flex-col items-center gap-2 p-4 text-center">
                    <AlertCircle className="h-8 w-8 text-danger" />
                    <span className="text-xs font-bold text-danger">Generation Failed</span>
                    <span className="text-[11px] text-text-muted max-w-xs">{error.message || String(error)}</span>
                  </div>
                ) : displayUrl ? (
                  <div className="flex flex-col gap-3 w-full h-full items-center justify-center">
                    {isVideo ? (
                      <video
                        src={displayUrl}
                        controls
                        autoPlay
                        loop
                        className="max-h-[380px] w-full rounded-md object-contain border border-border"
                      />
                    ) : (
                      <img
                        src={displayUrl}
                        alt="Generated Creative"
                        className="max-h-[380px] w-full rounded-md object-contain border border-border"
                      />
                    )}
                    <div className="flex items-center gap-2 w-full justify-between pt-2">
                      <span className="text-[10px] font-mono text-success flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" /> Completed
                      </span>
                      <a
                        href={displayUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] font-mono text-accent hover:underline flex items-center gap-1"
                      >
                        Open Full Asset <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-center text-text-faint p-6">
                    <ImageIcon className="h-10 w-10 stroke-[1.5]" />
                    <span className="text-xs font-medium text-text-muted">Asset Preview Ready</span>
                    <span className="text-[11px] text-text-faint max-w-xs">
                      Configure your prompt or pick a competitor ad above and click generate.
                    </span>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}

export default CreatePage
