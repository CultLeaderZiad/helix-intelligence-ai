import React, { useState, useEffect } from "react"
import { creativeService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { useSearchContext } from "@/context/SearchContext"
import { useLanguage } from "@/context/LanguageContext"
import { API_BASE_URL } from "@/services/config"
import { 
  Bookmark, 
  Trash2, 
  ExternalLink, 
  RefreshCw, 
  SearchX, 
  FolderPlus, 
  CheckCircle2, 
  Tag, 
  Film, 
  Image as ImageIcon,
  Plus,
  Link as LinkIcon,
  Sparkles,
  Download,
  Play,
  ArrowRight
} from "lucide-react"
import { Button } from "@/components/ui/Button"

export function SwipeFilesPage() {
  const { user } = useAuth()
  const { latestSearch } = useSearchContext()
  const { t, isRtl } = useLanguage()

  const [creatives, setCreatives] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeCollection, setActiveCollection] = useState("all")
  const [toast, setToast] = useState(null)
  
  // Custom Reference State
  const [showAddModal, setShowAddModal] = useState(false)
  const [customUrl, setCustomUrl] = useState("")
  const [customHeadline, setCustomHeadline] = useState("")
  const [customBody, setCustomBody] = useState("")
  const [customFormat, setCustomFormat] = useState("video")
  const [isSubmittingCustom, setIsSubmittingCustom] = useState(false)
  const [isSavingBulk, setIsSavingBulk] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  // Check if swipe_files feature flag is enabled
  const isFeatureEnabled = user?.feature_flags?.swipe_files !== false

  const fetchSaved = async () => {
    if (!isFeatureEnabled) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await creativeService.getSavedCreatives({
        collection: activeCollection === "all" ? null : activeCollection,
        page: 1,
        page_size: 50,
      })
      setCreatives(res.items || [])
    } catch (err) {
      setError(err.message || "Failed to load saved swipe file")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSaved()
  }, [activeCollection, isFeatureEnabled])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3500)
  }

  const handleUnsave = async (creativeId) => {
    try {
      await creativeService.unsaveCreative(creativeId)
      showToast(t("removedFromSwipe", "Creative removed from swipe file"))
      setCreatives((prev) => prev.filter((c) => c.id !== creativeId))
    } catch (err) {
      alert(err.message || "Failed to remove creative")
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    const MAX_SIZE = 2 * 1024 * 1024 // 2MB
    if (file.size > MAX_SIZE) {
      alert("File size exceeds 2MB limit. Please upload a smaller image to protect cache and avoid server corruption.")
      return
    }

    setIsUploading(true)
    const formData = new FormData()
    formData.append("file", file)

    try {
      const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token")
      const response = await fetch(`${API_BASE_URL}/media/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Upload failed")
      }

      const data = await response.json()
      setCustomUrl(data.url)
      setCustomFormat("image")
      showToast("Image file uploaded successfully!")
    } catch (err) {
      alert(err.message || "Failed to upload image file")
    } finally {
      setIsUploading(false)
    }
  }

  const handleAddCustom = async (e) => {
    e.preventDefault()
    if (!customUrl.trim() && !customHeadline.trim()) {
      alert("Please provide at least a URL or a headline/angle.")
      return
    }

    setIsSubmittingCustom(true)
    try {
      await creativeService.addCustomSwipeItem({
        url: customUrl.trim(),
        headline: customHeadline.trim() || (customUrl ? `Ad from ${new URL(customUrl.startsWith("http") ? customUrl : "https://" + customUrl).hostname}` : "Custom Ad Reference"),
        body: customBody.trim(),
        format: customFormat,
        collection: activeCollection === "all" ? "Default" : activeCollection,
      })
      showToast(t("refAdded", "Custom reference saved to swipe file"))
      setCustomUrl("")
      setCustomHeadline("")
      setCustomBody("")
      setShowAddModal(false)
      fetchSaved()
    } catch (err) {
      alert(err.message || "Failed to add reference")
    } finally {
      setIsSubmittingCustom(false)
    }
  }

  const handleSaveDiscoveredCorpus = async () => {
    if (!latestSearch?.items?.length) return
    setIsSavingBulk(true)
    try {
      const ids = latestSearch.items.map((c) => c.id)
      await creativeService.saveBulkCreatives(ids, latestSearch.query || "Discovered")
      showToast(`Saved ${ids.length} creatives from "${latestSearch.query}" to swipe files!`)
      fetchSaved()
    } catch (err) {
      alert(err.message || "Failed to save discovered ads")
    } finally {
      setIsSavingBulk(false)
    }
  }

  if (!isFeatureEnabled) {
    return (
      <div className="p-12 max-w-4xl mx-auto text-center space-y-4 font-sans">
        <Bookmark className="w-12 h-12 text-slate-500 mx-auto" />
        <h2 className="text-xl font-bold text-text">Swipe Files Feature Locked</h2>
        <p className="text-sm text-text-muted max-w-md mx-auto">
          Your current organization plan does not have the Swipe Files & Saved Collections feature enabled. Upgrade your plan or contact your workspace admin to unlock it.
        </p>
      </div>
    )
  }

  const discoveredCount = latestSearch?.items?.length || 0

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-sans">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold text-text flex items-center gap-3">
            <Bookmark className="w-6 h-6 text-accent" />
            {t("swipeFilesTitle", "Swipe Files & Saved Creatives")}
          </h1>
          <p className="text-text-muted text-xs mt-1">
            {t("swipeFilesSubtitle", "Personal swipe file library. Bookmark winning competitor ads or upload links/images (0 credits used).")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5 text-accent" />
            {t("addReference", "Add Ad Link / Reference")}
          </Button>

          <Button
            size="xs"
            variant="ghost"
            onClick={fetchSaved}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            {t("refresh", "Refresh")}
          </Button>
        </div>
      </div>

      {/* Discovered Corpus Import Banner */}
      {discoveredCount > 0 && (
        <div className="rounded-lg border border-accent/40 bg-surface-2 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent/10 border border-accent/30 text-accent">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-text">
                {t("discoveredAdsReady", "Discovered Ads Available")} ("{latestSearch.query}")
              </span>
              <p className="text-[11px] text-text-muted">
                {t("importPrompt", `Would you like to bookmark all ${discoveredCount} creatives from your latest search into your swipe file?`)}
              </p>
            </div>
          </div>

          <Button
            size="xs"
            variant="primary"
            onClick={handleSaveDiscoveredCorpus}
            disabled={isSavingBulk}
            className="shrink-0 flex items-center gap-1.5 text-xs font-bold"
          >
            <Download className="h-3.5 w-3.5 text-black" />
            {isSavingBulk ? t("saving", "Saving...") : t("saveAllToSwipe", `Save ${discoveredCount} Ads to Swipe File`)}
          </Button>
        </div>
      )}

      {toast && (
        <div className="p-3 bg-accent/10 border border-accent/30 rounded text-accent text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Add Reference Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-border bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-bold text-text flex items-center gap-2">
                <LinkIcon className="h-4 w-4 text-accent" />
                {t("addManualRef", "Add Ad Reference or Competitor Link")}
              </h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-text-faint hover:text-text text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddCustom} className="space-y-3">
              <div>
                <label className="label-mono text-text">{t("adUrl", "Ad or Landing Page URL")}</label>
                <input
                  type="text"
                  placeholder="https://facebook.com/ads/library/... or brand.com"
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  className="w-full rounded border border-border bg-surface-2 p-2 text-xs text-text placeholder-text-faint focus:border-accent focus:outline-none font-mono"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="label-mono text-text">Or Attach Image File (max 2MB)</label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    accept="image/png, image/jpeg, image/jpg, image/webp"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="swipe-file-upload"
                    disabled={isUploading}
                  />
                  <label
                    htmlFor="swipe-file-upload"
                    className="flex items-center gap-2 px-3 py-2 border border-border rounded bg-surface-2 text-xs font-semibold text-text cursor-pointer hover:bg-surface-3 transition"
                  >
                    <Plus className="w-3.5 h-3.5 text-accent" />
                    {isUploading ? "Uploading..." : "Choose Image"}
                  </label>
                  {customUrl && customUrl.startsWith("http") && (
                    <div className="flex items-center gap-2">
                      <img 
                        src={customUrl} 
                        alt="Attached Preview" 
                        className="h-8 w-8 object-cover rounded border border-border"
                      />
                      <span className="text-[11px] text-accent font-mono">Attached successfully</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="label-mono text-text">{t("headlineAngle", "Headline / Hook / Angle")}</label>
                <input
                  type="text"
                  placeholder="e.g. 'Stop wasting hours on manual editing...'"
                  value={customHeadline}
                  onChange={(e) => setCustomHeadline(e.target.value)}
                  className="w-full rounded border border-border bg-surface-2 p-2 text-xs text-text placeholder-text-faint focus:border-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="label-mono text-text">{t("notes", "Notes / Script Details")}</label>
                <textarea
                  rows={3}
                  placeholder="Key takeaways, visual breakdown, target audience..."
                  value={customBody}
                  onChange={(e) => setCustomBody(e.target.value)}
                  className="w-full rounded border border-border bg-surface-2 p-2 text-xs text-text placeholder-text-faint focus:border-accent focus:outline-none leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-4 pt-1">
                <label className="flex items-center gap-1.5 text-xs text-text cursor-pointer">
                  <input
                    type="radio"
                    name="format"
                    checked={customFormat === "video"}
                    onChange={() => setCustomFormat("video")}
                  />
                  <span>{t("video", "Video")}</span>
                </label>
                <label className="flex items-center gap-1.5 text-xs text-text cursor-pointer">
                  <input
                    type="radio"
                    name="format"
                    checked={customFormat === "image"}
                    onChange={() => setCustomFormat("image")}
                  />
                  <span>{t("image", "Image Still")}</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <Button
                  size="xs"
                  variant="ghost"
                  type="button"
                  onClick={() => setShowAddModal(false)}
                >
                  {t("cancel", "Cancel")}
                </Button>
                <Button
                  size="xs"
                  variant="primary"
                  type="submit"
                  disabled={isSubmittingCustom}
                >
                  {isSubmittingCustom ? t("saving", "Saving...") : t("saveReference", "Save to Swipe File")}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grid of Saved Creatives */}
      {loading ? (
        <div className="py-16 text-center text-text-muted font-mono text-xs">
          {t("loadingSwipe", "Loading saved swipe files...")}
        </div>
      ) : creatives.length === 0 ? (
        <div className="py-16 text-center bg-surface border border-border rounded-xl space-y-3">
          <SearchX className="w-10 h-10 text-text-faint mx-auto" />
          <h3 className="text-base font-bold text-text">{t("swipeEmpty", "Your swipe file is empty")}</h3>
          <p className="text-xs text-text-muted max-w-sm mx-auto">
            {t("swipeEmptyDesc", "Bookmark winning creatives while researching on Discover or click 'Add Ad Link' above to build your collection.")}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {creatives.map((c) => (
            <div
              key={c.id}
              className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm hover:border-border-strong transition flex flex-col justify-between"
            >
              {c.landing_domain && (c.landing_domain.startsWith("http") || c.landing_domain.includes("/uploads/")) && (
                <div className="w-full h-48 bg-surface-2 border-b border-border relative overflow-hidden flex items-center justify-center">
                  <img
                    src={c.landing_domain}
                    alt={c.headline || "Uploaded Ad Image"}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-mono font-medium px-2 py-0.5 rounded bg-surface-2 text-text border border-border uppercase">
                    {c.format === "video" ? <Film className="w-3.5 h-3.5 text-accent" /> : <ImageIcon className="w-3.5 h-3.5 text-text-muted" />}
                    {c.platform || "Ad"} · {c.format || "Media"}
                  </span>
                  <button
                    onClick={() => handleUnsave(c.id)}
                    title={t("removeSwipe", "Remove from swipe file")}
                    className="text-text-faint hover:text-danger p-1 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <h3 className="font-bold text-text text-sm line-clamp-2">
                  {c.headline || c.body || "Ad Reference"}
                </h3>

                <p className="text-xs text-text-muted line-clamp-3 leading-relaxed">
                  {c.body || "No body text available."}
                </p>

                {c.scores?.composite && (
                  <div className="pt-2 border-t border-border flex items-center justify-between text-xs font-mono">
                    <span className="text-text-faint">{t("compositeScore", "Composite Score")}</span>
                    <span className="text-accent font-bold">{c.scores.composite.toFixed(1)}/100</span>
                  </div>
                )}
              </div>

              <div className="p-3 bg-surface-2 border-t border-border flex items-center justify-between text-xs font-mono text-text-muted">
                <span className="truncate max-w-[150px]">{c.cta || c.landing_domain || "Reference"}</span>
                {c.days_active && (
                  <span className="text-text font-bold">
                    {c.days_active}d active
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  )
}

export default SwipeFilesPage
