import { useState, useEffect } from "react"
import { useSearchParams, useNavigate, Link } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import {
  Play,
  Image as ImageIcon,
  AlertCircle,
  Loader,
  Sparkles,
  Video,
  Wand2,
  ChevronDown,
  ArrowRight,
  Lock,
  RefreshCw,
  Settings2,
  Key,
  HelpCircle
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { creativeService } from "@/services"
import { useMediaGenerate } from "@/hooks/useMediaGenerate"
import { useSearchContext } from "@/context/SearchContext"
import { useAuth } from "@/context/AuthContext"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"
import { MessageSquarePlus } from "lucide-react"

const CREATIVE_MODES = {
  image: [
    { id: "premium_ad", label: "Commercial Ad Still (Default)", desc: "High-contrast photorealistic ad creative" },
    { id: "quick_concept", label: "Quick Concept", desc: "Fast ideation & concept variations" },
    { id: "cinematic_ad", label: "Cinematic Luxury", desc: "Dramatic lighting & editorial scene" },
    { id: "storyboard", label: "Storyboard Frame", desc: "Narrative scene keyframe" },
  ],
  video: [
    { id: "quick_video", label: "Quick Motion", desc: "Dynamic motion for social ads" },
    { id: "premium_video", label: "Commercial Video", desc: "High-fidelity commercial spot" },
    { id: "before_after", label: "Before → After", desc: "Transition between two keyframe states", requiresFrames: true },
    { id: "controlled_video", label: "Keyframed Video", desc: "Precise brand keyframe motion", requiresFrames: true },
  ]
}

const ASPECT_RATIOS = [
  { id: "1:1", label: "1:1 Square (Feed / Instagram)" },
  { id: "4:5", label: "4:5 Vertical (Instagram Feed)" },
  { id: "9:16", label: "9:16 Vertical (Stories / TikTok / Reels)" },
  { id: "16:9", label: "16:9 Landscape (YouTube / Desktop)" },
]

export function CreatePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const sourceId = searchParams.get("sourceId")
  const navigate = useNavigate()
  
  const { user } = useAuth()
  const { latestSearch, activeCreative, selectActiveCreative } = useSearchContext()
  
  const [sourceCreative, setSourceCreative] = useState(null)
  const [activeCategory, setActiveCategory] = useState("image")
  const [selectedMode, setSelectedMode] = useState("premium_ad")
  const [aspectRatio, setAspectRatio] = useState("1:1")
  const [brief, setBrief] = useState("")
  const [startImageUrl, setStartImageUrl] = useState("")
  const [showAdPicker, setShowAdPicker] = useState(false)
  const [isSupportOpen, setIsSupportOpen] = useState(false)
  const [customApiKey, setCustomApiKey] = useState("")
  const [customModel, setCustomModel] = useState("gemini-2.0-flash-lite-preview-02-05")
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  const { phase, job, result, error, submit, cancel, isBusy } = useMediaGenerate()

  const isTrial = user?.plan_id?.startsWith("plan_trial") || user?.plan === "trial" || user?.role !== "admin"
  const isAdmin = user?.role === "admin"
  
  // Image Limits
  const imagesUsedToday = user?.images_used_today || 0
  const imagesDailyLimit = user?.images_daily_limit || 5
  const imagesRemainingToday = user?.images_remaining_today !== undefined ? user.images_remaining_today : (imagesDailyLimit - imagesUsedToday)
  
  // Video Limits
  const videosUsedToday = user?.videos_used_today || 0
  const videosDailyLimit = user?.videos_daily_limit || 3
  const videosRemainingToday = user?.videos_remaining_today !== undefined ? user.videos_remaining_today : (videosDailyLimit - videosUsedToday)
  
  const remainingToday = activeCategory === "video" ? videosRemainingToday : imagesRemainingToday
  const dailyLimit = activeCategory === "video" ? videosDailyLimit : imagesDailyLimit
  const usedToday = activeCategory === "video" ? videosUsedToday : imagesUsedToday
  
  const daysLeft = user?.trial_days_remaining !== undefined ? user.trial_days_remaining : 7
  const isTrialExpired = user?.requires_plan || (isTrial && !isAdmin && daysLeft <= 0)
  const isDailyLimitReached = isTrial && !isAdmin && remainingToday <= 0

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

  const STYLE_PROMPTS = {
    premium_ad: "Photorealistic high-end commercial ad, crisp studio softbox lighting, razor sharp 8k commercial photography, award-winning composition, clean minimalist presentation.",
    quick_concept: "Dynamic social media UGC product showcase, vibrant natural daylight, eye-catching viral ad angle, highly engaging and authentic.",
    cinematic_ad: "Ultra-luxurious cinematic commercial scene, dramatic chiaroscuro lighting, dark textured stone pedestal, subtle golden rim reflections, editorial masterclass grade.",
    storyboard: "Narrative storytelling advertising keyframe, dynamic 35mm film camera perspective, rich cinematic atmosphere, compelling visual story.",
    quick_video: "Dynamic motion social video ad, fluid high-impact movement, vibrant social pacing.",
    premium_video: "High-production commercial video spot, elegant camera glide, crisp studio lighting transitions.",
    before_after: "High-contrast split comparison transition, product transformation showcase.",
    controlled_video: "Precision studio 3D rotation showcase, sleek product commercial presentation."
  }

  const PROMPT_TEMPLATES = [
    {
      title: "Hero Product Shot",
      desc: "Clean studio commercial on matte stone",
      prompt: "Photorealistic commercial studio ad of a premium modern product standing on a sleek textured stone podium, soft diffused rim lighting, crisp 8k product photography, award-winning visual."
    },
    {
      title: "UGC Social Ad",
      desc: "First-person hands-on showcase",
      prompt: "Authentic first-person view holding the product in natural ambient window lighting, clean lifestyle backdrop, subtle depth of field blur, high-converting social media visual."
    },
    {
      title: "Luxury Cinematic",
      desc: "Moody editorial with gold accents",
      prompt: "Dramatic dark moody luxury commercial setting with dark marble surfaces, warm golden rim reflections, subtle atmospheric haze, ultra-premium commercial quality."
    },
    {
      title: "Tech / App UI Mockup",
      desc: "3D floating device with glowing interface",
      prompt: "Futuristic sleek glass tablet floating in minimalist dark studio showcasing a vibrant glowing software interface, volumetric cyan and indigo lighting, 3D isometric commercial presentation."
    }
  ]

  function applyCreativeToBrief(creative, modeId = selectedMode) {
    setSourceCreative(creative)
    const brand = creative.brand_name ? `Brand: ${creative.brand_name}` : ""
    const headline = creative.headline ? `Ad Headline: "${creative.headline}"` : ""
    const hook = creative.scores?.hook ? `[Hook formula: ${creative.scores.hook}]` : ""
    const styleDesc = STYLE_PROMPTS[modeId] || STYLE_PROMPTS.premium_ad
    setBrief(
      `Commercial advertising creative remixing active campaign.\n${brand} ${headline} ${hook}\nStyle & Visual Direction: ${styleDesc}`
    )
  }

  const handleModeChange = (modeId) => {
    setSelectedMode(modeId)
    const styleDesc = STYLE_PROMPTS[modeId]
    if (styleDesc && brief) {
      if (brief.includes("Style & Visual Direction:")) {
        const parts = brief.split("Style & Visual Direction:")
        setBrief(`${parts[0].trim()}\nStyle & Visual Direction: ${styleDesc}`)
      } else {
        setBrief(`${brief.trim()}\nStyle & Visual Direction: ${styleDesc}`)
      }
    }
  }

  const handleCategoryChange = (category) => {
    setActiveCategory(category)
    if (category === "image") {
      setSelectedMode("premium_ad")
      setAspectRatio("1:1")
      if (sourceCreative) applyCreativeToBrief(sourceCreative, "premium_ad")
    } else {
      setSelectedMode("quick_video")
      setAspectRatio("9:16")
      if (sourceCreative) applyCreativeToBrief(sourceCreative, "quick_video")
    }
  }

  const handleGenerate = () => {
    if (!brief.trim() || isDailyLimitReached || isTrialExpired) return
    
    const params = {
      mode: selectedMode,
      aspect_ratio: aspectRatio,
      kind: activeCategory,
      source_creative_id: sourceCreative?.id || sourceId,
      reference_images: []
    }

    if (startImageUrl.trim()) {
      params.start_image_url = startImageUrl.trim()
      params.reference_images.push(startImageUrl.trim())
    }

    if (customApiKey.trim()) {
      params.custom_api_key = customApiKey.trim()
      params.custom_model = customModel
    }

    submit({
      prompt: brief,
      provider: "gemini",
      mode: selectedMode,
      parameters: params
    })
  }

  // Safe string conversion for error messages to prevent React crashes
  const displayErrorMessage = error
    ? (typeof error === "string" 
        ? error 
        : error?.message || error?.detail?.message || "Generation request failed. Please try again.")
    : null

  let displayUrl = null
  let isVideo = false
  if (result) {
    if (result.type === "video" && result.video?.url) {
      displayUrl = result.video.url
      isVideo = true
    } else if (result.type === "image" && result.image?.url) {
      displayUrl = result.image.url
    } else if (result.url) {
      displayUrl = result.url
      isVideo = displayUrl.endsWith(".mp4") || displayUrl.includes("video")
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
        meta={
          isAdmin 
            ? "Gemini Flash Image · Admin Unlimited"
            : `Trial: ${usedToday}/${dailyLimit} images today · ${daysLeft} days left`
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="ghost"
              onClick={() => setIsSupportOpen(true)}
              className="flex items-center gap-1 text-xs text-text-muted hover:text-text"
            >
              <MessageSquarePlus className="w-3.5 h-3.5 text-teal-400" />
              Report Issue
            </Button>
            {latestSearch ? (
              <Button size="xs" variant="ghost" onClick={() => navigate("/discover")}>
                From Search: "{latestSearch.query}" ({latestSearch.total} ads)
              </Button>
            ) : null}
          </div>
        }
      />

      <div className="flex-1 p-6 max-w-5xl mx-auto w-full">
        <div className="flex flex-col gap-6">

          {/* Trial Usage Indicator Bar */}
          {isTrial && !isAdmin && (
            <div className={`rounded-lg border p-4 flex items-center justify-between ${
              isTrialExpired 
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : isDailyLimitReached
                ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                : "border-primary/30 bg-primary/5 text-primary-light"
            }`}>
              <div className="flex items-center gap-3">
                <Sparkles className="h-5 w-5 text-primary" />
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-text">
                    {isTrialExpired 
                      ? "7-Day Free Trial Ended" 
                      : isDailyLimitReached 
                      ? `Daily ${activeCategory === "video" ? "Video" : "Image"} Limit Reached (${usedToday}/${dailyLimit})` 
                      : `7-Day Free Trial: ${usedToday} of ${dailyLimit} ${activeCategory === "video" ? "videos" : "images"} used today`}
                  </span>
                  <span className="text-[11px] text-text-muted">
                    {isTrialExpired 
                      ? "Upgrade to a paid plan to unlock unlimited image and video creation." 
                      : isDailyLimitReached 
                      ? `Your daily allowance resets at 00:00 UTC. Upgrade for 50+ ${activeCategory === "video" ? "videos" : "images"}/day.` 
                      : `${daysLeft} days remaining · ${activeCategory === "video" ? "Video motion trial active (3/day)." : "Video motion trial also active (3/day)."}`}
                  </span>
                </div>
              </div>

              {(isTrialExpired || isDailyLimitReached) && (
                <Link to="/billing">
                  <Button size="xs" variant="primary" className="font-semibold gap-1 text-black">
                    Upgrade Plan <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              )}
            </div>
          )}

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
                  Image Creative
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
                  Video Motion {isTrial && !isAdmin && <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-accent ml-1 font-mono font-bold">3/day Trial</span>}
                </button>
              </div>

              {/* Mode Selection */}
              <div className="flex flex-col gap-2">
                <label className="label-mono text-text">Creative Style</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {CREATIVE_MODES[activeCategory].map((mode) => (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => handleModeChange(mode.id)}
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

              {/* Prompt Assistant & Quick Formula Templates */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="label-mono text-text flex items-center gap-1.5">
                    <Wand2 className="w-3.5 h-3.5 text-accent" />
                    Prompt Assistant & 1-Click Formulas
                  </span>
                  <span className="text-[10px] font-mono text-text-faint">Click formula to apply</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {PROMPT_TEMPLATES.map((tmpl) => (
                    <button
                      key={tmpl.title}
                      type="button"
                      onClick={() => setBrief(tmpl.prompt)}
                      className="p-2.5 rounded-lg border border-border bg-surface hover:border-accent/50 text-left transition group"
                    >
                      <div className="text-xs font-semibold text-text group-hover:text-accent transition-colors">
                        {tmpl.title}
                      </div>
                      <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">
                        {tmpl.desc}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

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
                  placeholder="Describe the product, visual composition, lighting, camera angle, subject, and scene..."
                  className="w-full text-xs rounded-lg border border-border bg-surface p-3.5 text-text placeholder-text-faint focus:border-accent focus:outline-none font-sans leading-relaxed"
                />
              </div>

              {/* Optional Reference Image */}
              <div className="flex flex-col gap-2">
                <label className="label-mono text-text">Reference Image URL (Optional)</label>
                <input
                  type="url"
                  placeholder="https://example.com/product-or-style-reference.jpg"
                  value={startImageUrl}
                  onChange={(e) => setStartImageUrl(e.target.value)}
                  className="w-full text-xs rounded-lg border border-border bg-surface p-3 text-text placeholder-text-faint focus:border-accent focus:outline-none font-mono"
                />
              </div>

              {/* Bring Your Own Key / Advanced Options */}
              <div className="flex flex-col gap-2 border-t border-border pt-4 mt-2">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-xs font-semibold text-text-muted hover:text-text transition-colors w-fit"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  Bring Your Own Key (BYOK) & Advanced Options
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
                </button>

                {showAdvanced && (
                  <div className="flex flex-col gap-4 rounded-lg border border-border bg-surface-2 p-4 mt-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-accent" />
                        <label className="text-xs font-bold text-text">Custom Gemini API Key</label>
                      </div>
                      <a 
                        href="https://aistudio.google.com/app/apikey" 
                        target="_blank" 
                        rel="noreferrer"
                        className="flex items-center gap-1 text-[11px] text-accent hover:underline"
                      >
                        <HelpCircle className="w-3 h-3" /> Get a Free Key Guide
                      </a>
                    </div>
                    <p className="text-[11px] text-text-muted -mt-2">
                      Input your own API key to bypass limits or access premium models. Your key is only used for this session and is never stored permanently.
                    </p>
                    
                    <input
                      type="password"
                      placeholder="AIzaSy..."
                      value={customApiKey}
                      onChange={(e) => setCustomApiKey(e.target.value)}
                      className="w-full text-xs rounded-md border border-border bg-surface p-2.5 text-text focus:border-accent focus:outline-none font-mono"
                    />

                    {customApiKey && (
                      <div className="flex flex-col gap-2 mt-2">
                        <label className="text-xs font-bold text-text">Select Premium Model</label>
                        <select
                          value={customModel}
                          onChange={(e) => setCustomModel(e.target.value)}
                          className="w-full text-xs rounded-md border border-border bg-surface p-2.5 text-text focus:border-accent focus:outline-none"
                        >
                          <option value="gemini-2.0-flash-lite-preview-02-05">gemini-2.0-flash-lite (Fastest, Lowest Cost)</option>
                          <option value="gemini-2.5-flash-image">gemini-2.5-flash-image (Balanced)</option>
                          <option value="gemini-3.1-flash-image">gemini-3.1-flash-image (High Quality)</option>
                          <option value="gemini-3-pro-image">gemini-3-pro-image (Pro Quality)</option>
                          <option value="imagen-3.0-generate-002">imagen-3.0-generate-002 (Best for Photorealism)</option>
                        </select>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <Button
                size="md"
                variant="primary"
                onClick={handleGenerate}
                disabled={isBusy || !brief.trim() || isDailyLimitReached || isTrialExpired}
                className="w-full flex items-center justify-center gap-2 text-sm font-bold shadow-lg"
              >
                {isBusy ? (
                  <>
                    <Loader className="h-4 w-4 animate-spin text-black" />
                    {customApiKey.trim() ? "Generating with Gemini..." : "Generating Image..."}
                  </>
                ) : isTrialExpired ? (
                  "Trial Ended — Select a Plan to Generate"
                ) : isDailyLimitReached ? (
                  `Daily Limit Reached (${usedToday}/${dailyLimit} ${activeCategory === "video" ? "Videos" : "Images"} Used Today)`
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 text-black" />
                    {customApiKey.trim() ? "Generate with Gemini" : "Generate Image"}
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
                    <span className="text-xs font-semibold text-text">Gemini AI Generating Visual</span>
                    <span className="text-[11px] font-mono text-text-muted">
                      {job?.status ? `Status: ${job.status}` : "Synthesizing image concept..."}
                    </span>
                  </div>
                ) : displayErrorMessage ? (
                  <div className="flex flex-col items-center gap-3 text-center p-4">
                    <AlertCircle className="h-8 w-8 text-destructive" />
                    <span className="text-xs font-bold text-destructive">Generation Issue</span>
                    <p className="text-[11px] text-text-muted max-w-xs">{displayErrorMessage}</p>
                    <Button size="xs" variant="outline" onClick={handleGenerate} className="gap-1 text-xs mt-2">
                      <RefreshCw className="w-3 h-3" /> Retry Generation
                    </Button>
                  </div>
                ) : displayUrl ? (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-3">
                    <img
                      src={displayUrl}
                      alt="Generated AI Creative"
                      className="max-h-[320px] w-auto rounded-lg object-contain border border-border shadow-md"
                    />
                    <div className="flex items-center gap-2">
                      <a
                        href={displayUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-mono text-accent hover:underline flex items-center gap-1"
                      >
                        Open Full Asset <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-center text-text-faint">
                    <ImageIcon className="h-10 w-10 opacity-30" />
                    <span className="text-xs">Generated output will render here</span>
                    <span className="text-[11px] text-text-muted max-w-xs">
                      Select a competitor ad above or describe your creative brief to generate
                    </span>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>

      <SupportFeedbackModal
        isOpen={isSupportOpen}
        onClose={() => setIsSupportOpen(false)}
        initialContext={{ page: "Create Remix Studio", category: activeCategory, mode: selectedMode, tag: "create" }}
      />
    </div>
  )
}

export default CreatePage
