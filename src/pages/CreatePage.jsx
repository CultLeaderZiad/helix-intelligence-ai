import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { PenLine, Play, Image as ImageIcon, CheckCircle, AlertCircle, Loader } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { creativeService, mediaService } from "@/services"

export function CreatePage() {
  const [searchParams] = useSearchParams()
  const sourceId = searchParams.get("sourceId")
  
  const [sourceCreative, setSourceCreative] = useState(null)
  const [brief, setBrief] = useState("")
  const [generationMode, setGenerationMode] = useState("IMAGE_FAST")
  const [qualityIntent, setQualityIntent] = useState("1024x1024")
  
  const [isGenerating, setIsGenerating] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [resultUrl, setResultUrl] = useState(null)
  const [error, setError] = useState(null)

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

  useEffect(() => {
    let interval = null
    if (jobId && (jobStatus === "pending" || jobStatus === "in_progress")) {
      interval = setInterval(() => {
        mediaService.getJob(jobId).then((job) => {
          setJobStatus(job.status)
          if (job.status === "completed") {
            setResultUrl(job.result_url)
            setIsGenerating(false)
          } else if (job.status === "failed") {
            setError(job.error_message || "Generation failed")
            setIsGenerating(false)
          }
        }).catch(err => {
          console.error("Failed to poll job status", err)
        })
      }, 2000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [jobId, jobStatus])

  const handleGenerate = async () => {
    if (!brief.trim()) return
    
    setIsGenerating(true)
    setError(null)
    setJobId(null)
    setResultUrl(null)
    setJobStatus(null)
    
    try {
      const payload = {
        prompt: brief,
        provider: generationMode === "IMAGE_FAST" ? "higgsfield" : "mock",
        parameters: {
          resolution: qualityIntent,
          quality: "720p",
          source_creative_id: sourceId // Lineage
        }
      }
      
      const job = await mediaService.createJob(payload)
      setJobId(job.id)
      setJobStatus(job.status)
    } catch (err) {
      setError(err.message || "Failed to start generation")
      setIsGenerating(false)
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
                disabled={isGenerating}
              />
            </div>

            {/* Generation Mode */}
            <div className="flex flex-col gap-3">
              <label className="label-mono">Generation Mode</label>
              <div className="flex gap-2">
                {["IMAGE_FAST", "VIDEO_STANDARD"].map(mode => (
                  <Button 
                    key={mode} 
                    variant={generationMode === mode ? "primary" : "outline"}
                    onClick={() => setGenerationMode(mode)}
                    disabled={isGenerating}
                  >
                    {mode}
                  </Button>
                ))}
              </div>
            </div>

            {/* Quality Intent */}
            <div className="flex flex-col gap-3">
              <label className="label-mono">Quality Intent (Resolution)</label>
              <div className="flex gap-2">
                {["1024x1024", "16:9", "9:16"].map(intent => (
                  <Button 
                    key={intent} 
                    variant={qualityIntent === intent ? "primary" : "outline"}
                    onClick={() => setQualityIntent(intent)}
                    disabled={isGenerating}
                  >
                    {intent}
                  </Button>
                ))}
              </div>
            </div>
            
            <Button 
              variant="primary" 
              className="mt-4 w-full"
              disabled={!brief.trim() || isGenerating}
              onClick={handleGenerate}
            >
              {isGenerating ? "Generating..." : "Generate Asset"}
            </Button>
            
          </div>

          {/* Right Column: Output */}
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3">
              <label className="label-mono">Output</label>
              
              <div className="flex min-h-[400px] w-full flex-col items-center justify-center rounded border border-border bg-surface p-4 text-center">
                
                {!jobId && !resultUrl && !error && (
                  <div className="flex flex-col items-center gap-2 text-text-faint">
                    <PenLine className="h-8 w-8" />
                    <span className="text-sm">Ready to generate</span>
                  </div>
                )}

                {isGenerating && (
                  <div className="flex flex-col items-center gap-3">
                    <Loader className="h-8 w-8 animate-spin text-accent" />
                    <span className="text-sm text-text-muted">
                      {jobStatus === "pending" ? "Starting job..." : "Generating media, please wait..."}
                    </span>
                  </div>
                )}
                
                {error && (
                  <div className="flex flex-col items-center gap-3 text-red-500">
                    <AlertCircle className="h-8 w-8" />
                    <span className="text-sm">{error}</span>
                  </div>
                )}

                {resultUrl && !isGenerating && (
                  <div className="flex h-full w-full flex-col gap-3">
                    <div className="flex items-center gap-2 text-green-500">
                      <CheckCircle className="h-5 w-5" />
                      <span className="text-sm font-medium">Generation Complete</span>
                    </div>
                    <div className="relative flex min-h-0 flex-1 items-center justify-center bg-bg rounded overflow-hidden">
                      {resultUrl.endsWith(".mp4") ? (
                        <video src={resultUrl} controls autoPlay loop className="max-h-full max-w-full object-contain" />
                      ) : (
                        <img src={resultUrl} alt="Generated asset" className="max-h-full max-w-full object-contain" />
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
