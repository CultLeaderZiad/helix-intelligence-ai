import { useEffect, useState } from "react"
import { ArrowLeft, ArrowRight, Bookmark, Check, Clock, Plus, RotateCcw, Trash2, X } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { useSearchContext } from "@/context/SearchContext"
import { useLanguage } from "@/context/LanguageContext"
import { useW8Copy } from "@/i18n/w8Product"

/**
 * Search history and saved drafts. Both come from the server for workspaces
 * granted Discover, so they are the same on every page, browser and device.
 *
 * A history entry with stored results opens them; one without (a failed or
 * empty search) runs the search again, and the button says which it will do.
 *
 * @param {{
 *   isOpen: boolean, onClose: () => void,
 *   onSelectSearch?: (item: any) => void, onSelectDraft?: (draft: any) => void,
 *   currentQuery?: string, currentFilters?: Record<string, unknown>
 * }} props
 */
export function SavedDraftsModal({ isOpen, onClose, onSelectSearch, onSelectDraft, currentQuery = "", currentFilters = {} }) {
  const { searchHistory, drafts, saveDraft, deleteDraft, refreshFromServer, serverSynced } = useSearchContext()
  const { isRtl } = useLanguage()
  const c = useW8Copy()
  const [activeTab, setActiveTab] = useState("history")
  const [draftTitle, setDraftTitle] = useState("")
  const [draftNotes, setDraftNotes] = useState("")
  const [saving, setSaving] = useState(false)
  const [savedSuccess, setSavedSuccess] = useState(false)
  const [error, setError] = useState("")

  // Re-read the server each time the modal opens so another tab's or
  // device's searches and drafts show up.
  useEffect(() => {
    if (!isOpen) return
    setError("")
    void refreshFromServer?.()
  }, [isOpen, refreshFromServer])

  if (!isOpen) return null
  const Arrow = isRtl ? ArrowLeft : ArrowRight
  const query = currentQuery.trim()

  const handleSaveNewDraft = async (e) => {
    e.preventDefault()
    if (!query) {
      setError(c.draftsNeedQuery)
      return
    }
    setSaving(true)
    setError("")
    try {
      await saveDraft({ title: draftTitle.trim() || query, query, requirements: draftNotes.trim(), filters: currentFilters })
      setDraftTitle("")
      setDraftNotes("")
      setSavedSuccess(true)
      setTimeout(() => {
        setSavedSuccess(false)
        setActiveTab("drafts")
      }, 700)
    } catch {
      setError(c.draftsSaveFailed)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    setError("")
    try {
      await deleteDraft(id)
    } catch {
      setError(c.draftsDeleteFailed)
    }
  }

  const tabClass = (tab) =>
    `flex items-center gap-1.5 border-b-2 px-3 pb-2.5 font-mono text-xs font-medium transition-colors ${
      activeTab === tab ? "border-accent font-bold text-accent" : "border-transparent text-text-muted hover:text-text"
    }`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="drafts-modal-title">
      <div className="relative flex max-h-[85vh] w-full max-w-xl flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-border bg-surface-2 px-5 py-4">
          <div className="flex items-center gap-2">
            <Bookmark className="h-4 w-4 text-accent" aria-hidden="true" />
            <h2 id="drafts-modal-title" className="text-sm font-bold text-text">{c.draftsTitle}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label={c.draftsClose} className="rounded p-1 text-text-muted hover:bg-surface hover:text-text">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex flex-wrap border-b border-border bg-surface px-5 pt-2" role="tablist">
          <button type="button" role="tab" aria-selected={activeTab === "history"} onClick={() => setActiveTab("history")} className={tabClass("history")}>
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            {c.draftsHistoryTab(searchHistory.length)}
          </button>
          <button type="button" role="tab" aria-selected={activeTab === "drafts"} onClick={() => setActiveTab("drafts")} className={tabClass("drafts")}>
            <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />
            {c.draftsSavedTab(drafts.length)}
          </button>
          <button type="button" role="tab" aria-selected={activeTab === "new_draft"} onClick={() => setActiveTab("new_draft")} className={`ms-auto ${tabClass("new_draft")}`}>
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {c.draftsNewTab}
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-5">
          <p className="font-mono text-[10px] text-text-faint">{serverSynced ? c.draftsSyncedNote : c.draftsLocalNote}</p>
          {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}

          {activeTab === "history" && (
            <div className="space-y-2">
              {searchHistory.length === 0 ? (
                <div className="py-12 text-center font-mono text-xs text-text-faint">{c.draftsNoHistory}</div>
              ) : (
                searchHistory.map((item, idx) => {
                  const hasResults = (item.items?.length || 0) > 0 || ((item.total || 0) > 0 && item.status !== "failed")
                  return (
                    <div key={`${item.job_id || item.query}-${idx}`} className="group flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-surface-2 p-3 transition-all hover:border-accent/40">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-xs font-semibold text-text">{item.query}</span>
                          <span className="rounded border border-border bg-surface px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
                            {item.status === "failed" ? c.draftsFailed : c.draftsAds(item.total || item.items?.length || 0)}
                          </span>
                        </div>
                        <span className="mt-0.5 block font-mono text-[10px] text-text-faint">
                          {item.timestamp ? new Date(item.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : ""}
                        </span>
                      </div>
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => {
                          onSelectSearch?.(item)
                          onClose()
                        }}
                        className="flex shrink-0 items-center gap-1 text-xs group-hover:border-accent group-hover:text-accent"
                      >
                        {hasResults ? c.draftsOpenResults : c.draftsSearchAgain}
                        {hasResults ? <Arrow className="h-3 w-3" aria-hidden="true" /> : <RotateCcw className="h-3 w-3" aria-hidden="true" />}
                      </Button>
                    </div>
                  )
                })
              )}
            </div>
          )}

          {activeTab === "drafts" && (
            <div className="space-y-2">
              {drafts.length === 0 ? (
                <div className="py-12 text-center font-mono text-xs text-text-faint">{c.draftsNoDrafts}</div>
              ) : (
                drafts.map((draft) => (
                  <div key={draft.id} className="flex items-start justify-between gap-3 rounded-lg border border-border/60 bg-surface-2 p-3 transition-all hover:border-accent/40">
                    <div className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-bold text-text">{draft.title}</span>
                      {draft.query && <span className="mt-0.5 block font-mono text-[11px] text-accent">“{draft.query}”</span>}
                      {draft.requirements && (
                        <p className="mt-1 line-clamp-2 rounded border border-border/40 bg-surface p-1.5 font-mono text-[10px] text-text-muted">{draft.requirements}</p>
                      )}
                      <span className="mt-1 block font-mono text-[9px] text-text-faint">
                        {c.draftsSavedOn(new Date(draft.timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric" }))}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Button
                        size="xs"
                        variant="primary"
                        onClick={() => {
                          onSelectDraft?.(draft)
                          onClose()
                        }}
                        className="flex items-center gap-1 text-xs"
                      >
                        {c.draftsLoad} <Arrow className="h-3 w-3" aria-hidden="true" />
                      </Button>
                      <button type="button" onClick={() => handleDelete(draft.id)} className="rounded p-1 text-text-faint hover:bg-surface hover:text-danger" title={c.draftsDelete} aria-label={c.draftsDelete}>
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "new_draft" && (
            <form onSubmit={handleSaveNewDraft} className="space-y-4">
              <div>
                <label htmlFor="draft-title-input" className="mb-1 block font-mono text-xs text-text-muted">{c.draftsFieldTitle}</label>
                <input
                  id="draft-title-input"
                  type="text"
                  value={draftTitle}
                  maxLength={200}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  placeholder={query}
                  className="h-8 w-full rounded border border-border bg-surface-2 px-3 text-xs text-text focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label htmlFor="draft-target-input" className="mb-1 block font-mono text-xs text-text-muted">{c.draftsFieldQuery}</label>
                <input id="draft-target-input" type="text" value={currentQuery} readOnly className="h-8 w-full rounded border border-border bg-surface-2/50 px-3 text-xs text-text-muted" />
                <p className="mt-1 font-mono text-[10px] text-text-faint">{c.draftsFiltersNote}</p>
              </div>
              <div>
                <label htmlFor="draft-notes-input" className="mb-1 block font-mono text-xs text-text-muted">{c.draftsFieldNotes}</label>
                <textarea
                  id="draft-notes-input"
                  rows={3}
                  maxLength={2000}
                  value={draftNotes}
                  onChange={(e) => setDraftNotes(e.target.value)}
                  placeholder={c.draftsNotesPlaceholder}
                  className="w-full rounded border border-border bg-surface-2 p-2 text-xs text-text focus:border-accent focus:outline-none"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button size="sm" variant="outline" type="button" onClick={() => setActiveTab("drafts")}>{c.draftsCancel}</Button>
                <Button size="sm" variant="primary" type="submit" disabled={saving || !query} className="flex items-center gap-1.5 font-bold">
                  {savedSuccess ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />}
                  {savedSuccess ? c.draftsSaved : saving ? c.draftsSaving : c.draftsSave}
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
