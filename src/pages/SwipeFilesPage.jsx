import React, { useState, useEffect } from "react"
import { creativeService } from "@/services"
import { useAuth } from "@/context/AuthContext"
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
  Image as ImageIcon 
} from "lucide-react"

export default function SwipeFilesPage() {
  const { user } = useAuth()
  const [creatives, setCreatives] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeCollection, setActiveCollection] = useState("all")
  const [toast, setToast] = useState(null)

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
    setTimeout(() => setToast(null), 3000)
  }

  const handleUnsave = async (creativeId) => {
    try {
      await creativeService.unsaveCreative(creativeId)
      showToast("Creative removed from swipe file")
      setCreatives((prev) => prev.filter((c) => c.id !== creativeId))
    } catch (err) {
      alert(err.message || "Failed to remove creative")
    }
  }

  if (!isFeatureEnabled) {
    return (
      <div className="p-12 max-w-4xl mx-auto text-center space-y-4 font-sans">
        <Bookmark className="w-12 h-12 text-slate-600 mx-auto" />
        <h2 className="text-xl font-bold text-slate-200">Swipe Files Feature Locked</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Your current organization plan does not have the Swipe Files & Saved Collections feature enabled. Upgrade your plan or contact your workspace admin to unlock it.
        </p>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Bookmark className="w-7 h-7 text-indigo-400" />
            Swipe Files & Saved Creatives
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Personal swipe file library. Saving and organizing creatives is included in your plan (0 credits used).
          </p>
        </div>
        <button
          onClick={fetchSaved}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Grid of Saved Creatives */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 font-mono text-xs">
          Loading saved creatives...
        </div>
      ) : creatives.length === 0 ? (
        <div className="py-16 text-center bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
          <SearchX className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-300">Your swipe file is empty</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Bookmark winning creatives while researching on Discover to build your reference collection.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {creatives.map((c) => (
            <div
              key={c.id}
              className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-lg hover:border-slate-700 transition flex flex-col justify-between"
            >
              <div className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">
                    {c.format === "video" ? <Film className="w-3.5 h-3.5" /> : <ImageIcon className="w-3.5 h-3.5" />}
                    {c.platform} · {c.format}
                  </span>
                  <button
                    onClick={() => handleUnsave(c.id)}
                    title="Remove from swipe file"
                    className="text-slate-500 hover:text-rose-400 p-1 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <h3 className="font-bold text-slate-100 text-sm line-clamp-2">
                  {c.headline || c.body || "Creative without headline"}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-3">
                  {c.body || "No body text available."}
                </p>

                {c.scores?.composite && (
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-500">Composite Score</span>
                    <span className="text-indigo-400 font-bold">{c.scores.composite.toFixed(1)}/100</span>
                  </div>
                )}
              </div>

              <div className="p-4 bg-slate-950/60 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono text-slate-500">
                <span>{c.cta || "No CTA"}</span>
                {c.metrics?.impressions_est && (
                  <span className="text-amber-300">
                    ~{(c.metrics.impressions_est / 1000).toFixed(0)}k impr {c.is_estimated && <span className="text-[9px] text-amber-500">(est)</span>}
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
