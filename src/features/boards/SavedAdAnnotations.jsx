import { useState } from "react"
import { X } from "lucide-react"
import { boardService } from "@/services"
import { Button } from "@/components/ui/Button"
import { useW92Copy } from "@/i18n/w9_2Product"

const MAX_TAG = 40
const MAX_NOTE = 2000

/**
 * W9-2: tags and notes on one saved ad, edited in place on its board card.
 * State starts from what the saved-ads API returned and only changes after
 * the API confirms a write.
 * @param {{creativeId: string, tags?: string[], notes?: Array<{id: string, body: string, updated_at?: string|null}>, onTagsChange?: (tags: string[]) => void}} props
 */
export function SavedAdAnnotations({ creativeId, tags: initialTags = [], notes: initialNotes = [], onTagsChange }) {
  const w = useW92Copy()
  const [tags, setTags] = useState(initialTags)
  const [notes, setNotes] = useState(initialNotes)
  const [tagInput, setTagInput] = useState("")
  const [noteInput, setNoteInput] = useState("")
  const [editing, setEditing] = useState(null) // { id, body }
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function saveTags(next) {
    setBusy(true)
    setError(null)
    try {
      const res = await boardService.setTags(creativeId, next)
      setTags(res.tags)
      onTagsChange?.(res.tags)
    } catch {
      setError(w.tagsSaveFailed)
    } finally {
      setBusy(false)
    }
  }

  function addTag(event) {
    event.preventDefault()
    const tag = tagInput.trim().replace(/\s+/g, " ").toLowerCase().slice(0, MAX_TAG)
    if (!tag || tags.includes(tag)) {
      setTagInput("")
      return
    }
    setTagInput("")
    void saveTags([...tags, tag])
  }

  async function addNote(event) {
    event.preventDefault()
    const body = noteInput.trim()
    if (!body) return
    setBusy(true)
    setError(null)
    try {
      const note = await boardService.addNote(creativeId, body)
      setNotes((prev) => [...prev, note])
      setNoteInput("")
    } catch {
      setError(w.noteFailed)
    } finally {
      setBusy(false)
    }
  }

  async function saveEdit(event) {
    event.preventDefault()
    if (!editing?.body.trim()) return
    setBusy(true)
    setError(null)
    try {
      const note = await boardService.updateNote(creativeId, editing.id, editing.body.trim())
      setNotes((prev) => prev.map((n) => (n.id === note.id ? note : n)))
      setEditing(null)
    } catch {
      setError(w.noteFailed)
    } finally {
      setBusy(false)
    }
  }

  async function removeNote(noteId) {
    setBusy(true)
    setError(null)
    try {
      await boardService.deleteNote(creativeId, noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
    } catch {
      setError(w.noteFailed)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2 border-t border-border pt-2 text-xs" data-testid={`annotations-${creativeId}`}>
      <div>
        <span className="label-mono">{w.tagsLabel}</span>
        <ul className="mt-1 flex flex-wrap gap-1" aria-label={w.tagsLabel}>
          {tags.map((tag) => (
            <li key={tag} className="flex items-center gap-1 rounded bg-surface-2 px-1.5 py-0.5" dir="auto">
              {tag}
              <button
                type="button"
                className="text-text-faint hover:text-text"
                aria-label={w.removeTag(tag)}
                disabled={busy}
                onClick={() => saveTags(tags.filter((t) => t !== tag))}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
        <form onSubmit={addTag} className="mt-1 flex gap-1">
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            maxLength={MAX_TAG}
            dir="auto"
            placeholder={w.addTagPlaceholder}
            aria-label={w.addTagPlaceholder}
            className="min-w-0 flex-1 rounded border border-border bg-surface-2 px-2 py-1 text-xs text-text focus:border-accent focus:outline-none"
          />
          <Button type="submit" size="xs" variant="outline" disabled={busy || !tagInput.trim()}>{w.addTag}</Button>
        </form>
      </div>

      <div>
        <span className="label-mono">{w.notesLabel}</span>
        <ul className="mt-1 space-y-1">
          {notes.map((note) => (
            <li key={note.id} className="rounded bg-surface-2 p-1.5">
              {editing?.id === note.id ? (
                <form onSubmit={saveEdit} className="space-y-1">
                  <textarea
                    value={editing.body}
                    onChange={(e) => setEditing({ id: note.id, body: e.target.value })}
                    maxLength={MAX_NOTE}
                    dir="auto"
                    rows={2}
                    aria-label={w.editNote}
                    className="w-full rounded border border-border bg-surface p-1 text-xs text-text"
                  />
                  <div className="flex gap-1">
                    <Button type="submit" size="xs" disabled={busy}>{w.saveNote}</Button>
                    <Button type="button" size="xs" variant="ghost" onClick={() => setEditing(null)}>{w.cancel}</Button>
                  </div>
                </form>
              ) : (
                <>
                  <p className="whitespace-pre-wrap text-text" dir="auto">{note.body}</p>
                  <div className="mt-1 flex gap-2 text-[11px] text-text-faint">
                    {note.updated_at ? <span>{w.edited}</span> : null}
                    <button type="button" className="hover:text-text" onClick={() => setEditing({ id: note.id, body: note.body })}>{w.editNote}</button>
                    <button type="button" className="hover:text-danger" disabled={busy} onClick={() => removeNote(note.id)}>{w.deleteNote}</button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
        <form onSubmit={addNote} className="mt-1 space-y-1">
          <textarea
            value={noteInput}
            onChange={(e) => setNoteInput(e.target.value)}
            maxLength={MAX_NOTE}
            dir="auto"
            rows={2}
            placeholder={w.addNotePlaceholder}
            aria-label={w.addNotePlaceholder}
            className="w-full rounded border border-border bg-surface-2 p-1.5 text-xs text-text focus:border-accent focus:outline-none"
          />
          <Button type="submit" size="xs" variant="outline" disabled={busy || !noteInput.trim()}>{w.addNote}</Button>
        </form>
      </div>
      {error ? <p role="alert" className="text-danger">{error}</p> : null}
    </div>
  )
}
