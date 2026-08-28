import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { PenLine, Play, Image as ImageIcon, CheckCircle, AlertCircle, Loader } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { creativeService } from "@/services"
import { useMediaGenerate, PHASE } from "@/hooks/useMediaGenerate"

export function CreatePage() {
  const [searchParams] = useSearchParams()
  const sourceId = searchParams.get("sourceId")
  
  const [sourceCreative, setSourceCreative] = useState(null)
  const [brief, setBrief] = useState("")
  const [generationMode, setGenerationMode] = useState("IMAGE_FAST")
  
  const { phase, job, result, error, submit, cancel, isBusy } = useMediaGenerate()

  useEffect(() => {
    if (sourceId) {
      creativeService.getCreativeById(sourceId).then((creative) => {
        setSourceCreative(creative)
        if (creative) {
          setBrief(`Remix of ${creative.headline}\n\nMaintain the original hook and visual style, but apply to a new product variation.`)
        }
      }).catch(err => {
        console.error("Failed to load source creative", err)
      })
    }
  }, [sourceId])

  const handleGenerate = () => {
    if (!brief.trim()) return
    submit({
      prompt: brief,
      provider: "higgsfield",
      parameters: {
        model: generationMode === "VIDEO_STANDARD" ? "soul_v2" : "soul_v2",
        resolution: "1024x1024",
        kind: generationMode === "VIDEO_STANDARD" ? "video" : "image",
        source_creative_id: sourceId
      }
    })
  }

  let displayUrl = null
  let isVideo = false
  if (result) {
    if (result.type === "video" && result.video?.url) {
      displayUrl = result.video.url
    } else if (result.type === "image" && result.images?.[0]?.url) {
      displayUrl = result.images[0].url
    } else if (result.url) {
      displayUrl = result.url
    }
    
    if (displayUrl) {
      isVideo = displayUrl.includes(".mp4") || displayUrl.includes("video") || generationMode === "VIDEO_STANDARD"
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar trail={["Helix", "Create"]} />
      
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 p-6">
        
        {/* Header */}
        <div className="flex flex-col gap-2">
          <h1 className="text-xl font-medium text-text">Create Media</h1>
          <p className="text-sm text-text-muted">Draft new creative briefed on the patterns that win.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Left Column: Inputs */}
          <div className="flex flex-col gap-6">
            
            {/* Source Section */}
            <div className="flex flex-col gap-3">
              <label className="label-mono">Source</label>
              {sourceCreative ? (
                <div className="flex items-center gap-4 border border-border bg-surface p-3 rounded">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-bg">
                    {sourceCreative.format === "video" ? <Play className="h-5 w-5 text-text-faint" /> : <ImageIcon className="h-5 w-5 text-text-faint" />}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="truncate text-sm font-medium">{sourceCreative.headline}</span>
                    <span className="truncate text-xs text-text-muted">{sourceCreative.brand?.name || "Unknown Brand"}</span>
                  </div>
                </div>
              ) : (
                <div className="border border-dashed border-border p-4 text-center text-sm text-text-muted rounded">
                  No source creative selected. Start from scratch or select one in Discover.
                </div>
              )}
            </div>

            {/* Brief Section */}
            <div className="flex flex-col gap-3">
              <label className="label-mono">Creative Brief</label>
              <textarea 
                className="min-h-[120px] w-full resize-y rounded border border-border bg-bg p-3 text-sm text-text placeholder-text-faint focus:border-accent focus:outline-none"
                placeholder="Describe the asset you want to generate..."
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                disabled={isBusy}
              />
            </div>

            {/* Generation Mode */}
            <div className="flex flex-col gap-3">
              <label className="label-mono">Generation Provider</label>
              <div className="flex flex-wrap gap-2">
                {["IMAGE_FAST", "VIDEO_STANDARD"].map(mode => (
                  <Button 
                    key={mode} 
                    variant={generationMode === mode ? "primary" : "outline"}
                    onClick={() => setGenerationMode(mode)}
                    disabled={isBusy}
                  >
                    {mode.replace("_", " ")}
                  </Button>
                ))}
              </div>
            </div>
            
            {isBusy ? (
              <Button 
                variant="outline" 
                className="mt-4 w-full border-red-500/50 text-red-500 hover:bg-red-500/10 hover:text-red-400"
                onClick={cancel}
              >
                Cancel Generation
              </Button>
            ) : (
              <Button 
                variant="primary" 
                className="mt-4 w-full"
                disabled={!brief.trim()}
                onClick={handleGenerate}
              >
                Generate Asset
              </Button>
            )}
            
          </div>

          {/* Right Column: Output */}
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3">
              <label className="label-mono">Output</label>
              
              <div className="flex min-h-[400px] w-full flex-col items-center justify-center rounded border border-border bg-surface p-4 text-center">
                
                {phase === PHASE.IDLE && (
                  <div className="flex flex-col items-center gap-2 text-text-faint">
                    <PenLine className="h-8 w-8" />
                    <span className="text-sm">Ready to generate</span>
                  </div>
                )}

                {isBusy && (
                  <div className="flex flex-col items-center gap-4 w-full max-w-xs">
                    <Loader className="h-8 w-8 animate-spin text-accent" />
                    <div className="flex flex-col gap-1 w-full text-center">
                      <span className="text-sm font-medium text-text">
                        {job?.stage_label || "Starting job..."}
                      </span>
                      {job?.progress !== undefined && (
                        <div className="h-1.5 w-full bg-border rounded overflow-hidden mt-2">
                          <div 
                            className="h-full bg-accent transition-all duration-500" 
                            style={{ width: `${Math.max(5, job.progress * 100)}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {phase === PHASE.ERROR && (
                  <div className="flex flex-col items-center gap-3 text-red-500">
                    <AlertCircle className="h-8 w-8" />
                    <span className="text-sm">{error?.message || "Generation failed"}</span>
                  </div>
                )}

                {phase === PHASE.READY && displayUrl && (
                  <div className="flex h-full w-full flex-col gap-3">
                    <div className="flex items-center gap-2 text-green-500">
                      <CheckCircle className="h-5 w-5" />
                      <span className="text-sm font-medium">Generation Complete</span>
                    </div>
                    <div className="relative flex min-h-0 flex-1 items-center justify-center bg-bg rounded overflow-hidden">
                      {isVideo ? (
                        <video src={displayUrl} controls autoPlay loop className="max-h-full max-w-full object-contain" />
                      ) : (
                        <img src={displayUrl} alt="Generated asset" className="max-h-full max-w-full object-contain" />
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

