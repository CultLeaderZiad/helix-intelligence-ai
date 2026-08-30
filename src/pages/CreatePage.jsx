import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { PenLine, Play, Image as ImageIcon, CheckCircle, AlertCircle, Loader, Sparkles, Video, Film, Wand2 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { creativeService } from "@/services"
import { useMediaGenerate, PHASE } from "@/hooks/useMediaGenerate"

const CREATIVE_MODES = {
  image: [
    { id: "premium_ad", label: "Premium Ad", desc: "Soul 2 photorealistic commercial still (Default)" },
    { id: "quick_concept", label: "Quick Concept", desc: "Popcorn fast ideation & variations" },
    { id: "cinematic_ad", label: "Cinematic Ad", desc: "Soul Cinema luxury & dramatic lighting" },
    { id: "storyboard", label: "Storyboard", desc: "Popcorn multi-angle narrative sequence" },
  ],
  video: [
    { id: "quick_video", label: "Quick Video", desc: "DoP Turbo fast motion for social testing" },
    { id: "premium_video", label: "Premium Video", desc: "DoP Standard high-fidelity commercial" },
    { id: "before_after", label: "Before → After", desc: "DoP FLF transition between two states", requiresFrames: true },
    { id: "controlled_video", label: "Controlled Video", desc: "DoP Standard Keyframed brand video", requiresFrames: true },
  ]
}

const ASPECT_RATIOS = [
  { id: "1:1", label: "1:1 Square (Feed / Instagram)" },
  { id: "9:16", label: "9:16 Vertical (Stories / TikTok / Reels)" },
  { id: "16:9", label: "16:9 Landscape (YouTube / Desktop)" },
]

export function CreatePage() {
  const [searchParams] = useSearchParams()
  const sourceId = searchParams.get("sourceId")
  
  const [sourceCreative, setSourceCreative] = useState(null)
  const [activeCategory, setActiveCategory] = useState("image")
  const [selectedMode, setSelectedMode] = useState("premium_ad")
  const [aspectRatio, setAspectRatio] = useState("1:1")
  const [brief, setBrief] = useState("")
  const [startImageUrl, setStartImageUrl] = useState("")
  const [endImageUrl, setEndImageUrl] = useState("")
  
  const { phase, job, result, error, submit, cancel, isBusy } = useMediaGenerate()

  useEffect(() => {
    if (sourceId) {
      creativeService.getCreativeById(sourceId).then((creative) => {
        setSourceCreative(creative)
        if (creative) {
          const headline = creative.headline ? `Headline: "${creative.headline}"` : ""
          const hook = creative.scores?.hook ? `[Hook score: ${creative.scores.hook}]` : ""
          const cta = creative.cta ? `Call-to-action: "${creative.cta}"` : ""
          setBrief(
            `Editorial commercial ad still remixing competitor pattern.\n${headline} ${hook}\n${cta}\nSetting: modern minimalist studio, bold dramatic side lighting, high contrast, clean background, 35mm photography, 8k commercial quality, no watermarks.`
          )
        }
      }).catch(err => {
        console.error("Failed to load source creative", err)
      })
    }
  }, [sourceId])

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
      source_creative_id: sourceId
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
    } else if (result.type === "image" && result.images?.[0]?.url) {
      displayUrl = result.images[0].url
    } else if (result.url) {
      displayUrl = result.url
    }
    
    if (displayUrl) {
      isVideo = displayUrl.includes(".mp4") || displayUrl.includes("video") || activeCategory === "video"
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar trail={["Helix", "Create"]} />
      
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
        
        {/* Header */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-accent" />
            <h1 className="text-xl font-medium text-text">Create Media Studio</h1>
          </div>
          <p className="text-sm text-text-muted">
            Transform winning intelligence patterns into high-converting image and video ads powered by Higgsfield.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Inputs & Controls (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            
            {/* Category Switcher (Image vs Video) */}
            <div className="flex gap-2 p-1 bg-surface rounded-lg border border-border">
              <button
                type="button"
                onClick={() => handleCategoryChange("image")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeCategory === "image"
                    ? "bg-bg text-text shadow-sm border border-border"
                    : "text-text-muted hover:text-text"
                }`}
              >
                <ImageIcon className="h-4 w-4" />
                Image Generation
              </button>
              <button
                type="button"
                onClick={() => handleCategoryChange("video")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeCategory === "video"
                    ? "bg-bg text-text shadow-sm border border-border"
                    : "text-text-muted hover:text-text"
                }`}
              >
                <Video className="h-4 w-4" />
                Video Generation
              </button>
            </div>

            {/* Mode Selection */}
            <div className="flex flex-col gap-2">
              <label className="label-mono">Creative Mode</label>
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
                    <span className="text-sm font-medium text-text">{mode.label}</span>
                    <span className="text-xs text-text-muted mt-1 leading-relaxed">{mode.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Aspect Ratio Selection */}
            <div className="flex flex-col gap-2">
              <label className="label-mono">Aspect Ratio</label>
              <div className="flex flex-wrap gap-2">
                {ASPECT_RATIOS.map((ratio) => (
                  <button
                    key={ratio.id}
                    type="button"
                    onClick={() => setAspectRatio(ratio.id)}
                    className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                      aspectRatio === ratio.id
                        ? "border-accent bg-accent/10 text-accent font-medium"
                        : "border-border bg-surface text-text-muted hover:text-text"
                    }`}
                  >
                    {ratio.label}
                  </button>
                ))}
              </div>
            </div>

            {/* First-Last Frame Inputs if applicable */}
            {isModeRequiringFrames && (
              <div className="flex flex-col gap-3 p-4 rounded-lg border border-accent/30 bg-accent/5">
                <div className="flex items-center gap-2 text-xs font-medium text-accent">
                  <Film className="h-4 w-4" />
                  Keyframe References (First & Last Frame)
                </div>
                <div className="flex flex-col gap-2">
                  <input
                    type="url"
                    placeholder="Start Image URL (e.g. initial product/problem state)"
                    value={startImageUrl}
                    onChange={(e) => setStartImageUrl(e.target.value)}
                    className="w-full text-xs rounded border border-border bg-bg p-2.5 text-text placeholder-text-faint focus:border-accent focus:outline-none"
                  />
                  <input
                    type="url"
                    placeholder="End Image URL (e.g. final result/solved state)"
                    value={endImageUrl}
                    onChange={(e) => setEndImageUrl(e.target.value)}
                    className="w-full text-xs rounded border border-border bg-bg p-2.5 text-text placeholder-text-faint focus:border-accent focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Source Creative Banner */}
            {sourceCreative && (
              <div className="flex items-center gap-3 border border-border bg-surface p-3 rounded-lg">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center bg-bg rounded">
                  {sourceCreative.format === "video" ? (
                    <Play className="h-4 w-4 text-text-faint" />
                  ) : (
                    <ImageIcon className="h-4 w-4 text-text-faint" />
                  )}
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="truncate text-xs font-medium text-text">Source: {sourceCreative.headline || "Competitor Ad"}</span>
                  <span className="truncate text-[11px] text-text-muted">{sourceCreative.brand?.name || "Competitor Creative"}</span>
                </div>
              </div>
            )}

            {/* Brief Section with Structured Prompt Guidelines */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="label-mono">Generation Prompt</label>
                <span className="text-[11px] text-text-muted flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-accent" /> Include subject, lighting, style & CTA
                </span>
              </div>
              <textarea 
                className="min-h-[140px] w-full resize-y rounded-lg border border-border bg-bg p-3 text-sm text-text placeholder-text-faint focus:border-accent focus:outline-none leading-relaxed font-sans"
                placeholder="Example: Editorial product still of a matte black water bottle on wet dark slate, hard side lighting, 35mm lens, high contrast commercial ad, 8k photorealistic, no watermarks"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                disabled={isBusy}
              />
            </div>
            
            {isBusy ? (
              <Button 
                variant="outline" 
                className="w-full border-red-500/50 text-red-500 hover:bg-red-500/10 hover:text-red-400"
                onClick={cancel}
              >
                Cancel Generation
              </Button>
            ) : (
              <Button 
                variant="primary" 
                className="w-full py-2.5 font-medium shadow-md shadow-accent/10"
                disabled={!brief.trim()}
                onClick={handleGenerate}
              >
                Generate Creative Asset
              </Button>
            )}
            
          </div>

          {/* Right Column: Output & Preview (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <label className="label-mono">Creative Output</label>
              
              <div className="flex min-h-[420px] w-full flex-col items-center justify-center rounded-lg border border-border bg-surface p-4 text-center">
                
                {phase === PHASE.IDLE && (
                  <div className="flex flex-col items-center gap-3 text-text-faint p-6">
                    <div className="h-12 w-12 rounded-full bg-bg border border-border flex items-center justify-center">
                      <PenLine className="h-6 w-6 text-text-muted" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium text-text">Ready to generate</span>
                      <span className="text-xs text-text-muted">Select a mode and craft your prompt to generate real media via Higgsfield.</span>
                    </div>
                  </div>
                )}

                {isBusy && (
                  <div className="flex flex-col items-center gap-4 w-full max-w-xs p-6">
                    <Loader className="h-8 w-8 animate-spin text-accent" />
                    <div className="flex flex-col gap-1 w-full text-center">
                      <span className="text-sm font-medium text-text">
                        {job?.stage_label || "Generating with Higgsfield..."}
                      </span>
                      <span className="text-xs text-text-muted">
                        Processing via {selectedMode.replace("_", " ")}
                      </span>
                      {job?.progress !== undefined && (
                        <div className="h-1.5 w-full bg-border rounded-full overflow-hidden mt-3">
                          <div 
                            className="h-full bg-accent transition-all duration-500 rounded-full" 
                            style={{ width: `${Math.max(10, (job.progress || 0.1) * 100)}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {phase === PHASE.ERROR && (
                  <div className="flex flex-col items-center gap-3 text-red-500 p-6">
                    <AlertCircle className="h-8 w-8 text-red-500" />
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium">Generation Error</span>
                      <span className="text-xs text-red-400 max-w-xs">{error?.message || "Generation failed"}</span>
                    </div>
                  </div>
                )}

                {phase === PHASE.READY && displayUrl && (
                  <div className="flex h-full w-full flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-green-500">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-xs font-medium">Asset Ready</span>
                      </div>
                      <a 
                        href={displayUrl} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="text-xs text-accent hover:underline"
                      >
                        Open Full Resolution ↗
                      </a>
                    </div>
                    <div className="relative flex min-h-[320px] flex-1 items-center justify-center bg-bg rounded-lg overflow-hidden border border-border">
                      {isVideo ? (
                        <video 
                          src={displayUrl} 
                          controls 
                          autoPlay 
                          loop 
                          className="max-h-[380px] max-w-full object-contain rounded" 
                        />
                      ) : (
                        <img 
                          src={displayUrl} 
                          alt="Generated asset" 
                          className="max-h-[380px] max-w-full object-contain rounded" 
                        />
                      )}
                    </div>
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
