import { useState } from "react"
import { Bookmark, Clock, Trash2, ArrowRight, Plus, X, Search, Sparkles, Check } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Panel } from "@/components/ui/Panel"
import { useSearchContext } from "@/context/SearchContext"

export function SavedDraftsModal({ isOpen, onClose, onSelectSearch, onSelectDraft, currentQuery = "" }) {
  const { searchHistory, drafts, saveDraft, deleteDraft } = useSearchContext()
  const [activeTab, setActiveTab] = useState("history") // 'history' | 'drafts'
  const [draftTitle, setDraftTitle] = useState("")
  const [draftNotes, setDraftNotes] = useState("")
  const [savedSuccess, setSavedSuccess] = useState(false)

  if (!isOpen) return null

  const handleSaveNewDraft = (e) => {
    e.preventDefault()
    if (!currentQuery.trim() && !draftTitle.trim()) return

    saveDraft({
      title: draftTitle.trim() || currentQuery.trim(),
      query: currentQuery.trim() || draftTitle.trim(),
      requirements: draftNotes.trim(),
      timestamp: new Date().toISOString()
    })

    setDraftTitle("")
    setDraftNotes("")
    setSavedSuccess(true)
    setTimeout(() => {
      setSavedSuccess(false)
      setActiveTab("drafts")
    }, 800)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-xl rounded-xl border border-border bg-surface shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-surface-2">
          <div className="flex items-center gap-2">
            <Bookmark className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-bold text-text">Searches & Saved Drafts</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-text-muted hover:bg-surface hover:text-text"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-border bg-surface px-5 pt-2">
          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-1.5 pb-2.5 px-3 text-xs font-mono font-medium border-b-2 transition-colors ${
              activeTab === "history"
                ? "border-accent text-accent font-bold"
                : "border-transparent text-text-muted hover:text-text"
            }`}
          >
            <Clock className="h-3.5 w-3.5" />
            Search History ({searchHistory.length})
          </button>
          <button
            onClick={() => setActiveTab("drafts")}
            className={`flex items-center gap-1.5 pb-2.5 px-3 text-xs font-mono font-medium border-b-2 transition-colors ${
              activeTab === "drafts"
                ? "border-accent text-accent font-bold"
                : "border-transparent text-text-muted hover:text-text"
            }`}
          >
            <Bookmark className="h-3.5 w-3.5" />
            Saved Drafts ({drafts.length})
          </button>
          <button
            onClick={() => setActiveTab("new_draft")}
            className={`ml-auto flex items-center gap-1 pb-2.5 px-2 text-xs font-mono text-text-muted hover:text-accent transition-colors ${
              activeTab === "new_draft" ? "border-b-2 border-accent text-accent font-bold" : ""
            }`}
          >
            <Plus className="h-3.5 w-3.5" />
            Save Current as Draft
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          
          {/* TAB 1: SEARCH HISTORY */}
          {activeTab === "history" && (
            <div className="space-y-2">
              {searchHistory.length === 0 ? (
                <div className="py-12 text-center text-xs font-mono text-text-faint">
                  No search history recorded yet.
                </div>
              ) : (
                searchHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-surface-2 p-3 hover:border-accent/40 transition-all group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-text truncate">
                          {item.query}
                        </span>
                        <span className="font-mono text-[10px] text-text-muted rounded bg-surface px-1.5 py-0.5 border border-border">
                          {item.total || item.items?.length || 0} ads
                        </span>
                        {item.category_label && (
                          <span className="font-mono text-[9px] text-accent/80 truncate hidden sm:inline">
                            {item.category_label}
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-[10px] text-text-faint block mt-0.5">
                        {item.timestamp ? new Date(item.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : "Recent"}
                      </span>
                    </div>

                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => {
                        onSelectSearch?.(item)
                        onClose()
                      }}
                      className="shrink-0 flex items-center gap-1 text-xs group-hover:border-accent group-hover:text-accent"
                    >
                      Use Search <ArrowRight className="h-3 w-3" />
                    </Button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 2: SAVED DRAFTS */}
          {activeTab === "drafts" && (
            <div className="space-y-2">
              {drafts.length === 0 ? (
                <div className="py-12 text-center text-xs font-mono text-text-faint">
                  No saved drafts yet. Click "Save Current as Draft" above to store your search brief.
                </div>
              ) : (
                drafts.map((draft) => (
                  <div
                    key={draft.id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-border/60 bg-surface-2 p-3 hover:border-accent/40 transition-all"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-bold text-xs text-text block truncate">
                        {draft.title}
                      </span>
                      {draft.query && (
                        <span className="font-mono text-[11px] text-accent block mt-0.5">
                          Query: "{draft.query}"
                        </span>
                      )}
                      {draft.requirements && (
                        <p className="font-mono text-[10px] text-text-muted line-clamp-2 mt-1 bg-surface p-1.5 rounded border border-border/40">
                          {draft.requirements}
                        </p>
                      )}
                      <span className="font-mono text-[9px] text-text-faint block mt-1">
                        Saved: {new Date(draft.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button
                        size="xs"
                        variant="primary"
                        onClick={() => {
                          onSelectDraft?.(draft)
                          onClose()
                        }}
                        className="flex items-center gap-1 text-xs"
                      >
                        Load Draft <ArrowRight className="h-3 w-3" />
                      </Button>
                      <button
                        onClick={() => deleteDraft(draft.id)}
                        className="rounded p-1 text-text-faint hover:text-red-400 hover:bg-surface"
                        title="Delete draft"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 3: NEW DRAFT FORM */}
          {activeTab === "new_draft" && (
            <form onSubmit={handleSaveNewDraft} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-text-muted mb-1">
                  Draft Title / Name
                </label>
                <input
                  type="text"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  placeholder={currentQuery || "e.g. Q4 Competitor Campaign"}
                  className="w-full h-8 rounded border border-border bg-surface-2 px-3 text-xs text-text focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-text-muted mb-1">
                  Search Target / Competitor
                </label>
                <input
                  type="text"
                  value={currentQuery}
                  readOnly
                  className="w-full h-8 rounded border border-border bg-surface-2/50 px-3 text-xs text-text-muted"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-text-muted mb-1">
                  Creative Requirements & Strategy Notes
                </label>
                <textarea
                  rows={3}
                  value={draftNotes}
                  onChange={(e) => setDraftNotes(e.target.value)}
                  placeholder="e.g. Focus on hook retention, test 9:16 vertical reels, benchmark against winner format..."
                  className="w-full rounded border border-border bg-surface-2 p-2 text-xs text-text focus:outline-none focus:border-accent"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button size="sm" variant="outline" type="button" onClick={() => setActiveTab("drafts")}>
                  Cancel
                </Button>
                <Button size="sm" variant="accent" type="submit" className="flex items-center gap-1.5 font-bold">
                  {savedSuccess ? <Check className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
                  {savedSuccess ? "Saved!" : "Save Draft"}
                </Button>
              </div>
            </form>
          )}

        </div>

      </div>
    </div>
  )
}
export default SavedDraftsModal
