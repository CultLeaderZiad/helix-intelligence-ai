import { useCallback, useEffect, useState } from "react"
import { Archive, ArchiveRestore, MessageSquarePlus, Pin, PinOff, Trash2 } from "lucide-react"
import agentService from "@/services/api/agentService.api"

function formatDate(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang === "ar" ? "ar" : "en", { month: "short", day: "numeric" })
  } catch {
    return ""
  }
}

/**
 * The user's saved Ask Helix conversations: open, pin, archive or delete one, or start a new chat.
 * Nothing is removed unless the user presses delete twice; past the limit the server archives
 * the oldest unpinned conversation instead of deleting it.
 */
export function ConversationHistory({ c, lang, activeId, refreshKey, onOpen, onNew, onRemoved, disabled = false }) {
  const [tab, setTab] = useState("active")
  const [items, setItems] = useState(null)
  const [max, setMax] = useState(50)
  const [failed, setFailed] = useState(false)
  const [confirming, setConfirming] = useState(null)

  const load = useCallback(async () => {
    try {
      const res = await agentService.conversations(tab === "archived")
      setItems(res?.items ?? [])
      setMax(res?.max_active ?? 50)
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }, [tab])

  useEffect(() => { void load() }, [load, refreshKey])

  async function patch(id, body) {
    setFailed(false)
    try {
      await agentService.updateConversation(id, body)
      await load()
    } catch {
      setFailed(true)
    }
  }

  async function remove(id) {
    if (confirming !== id) {
      setConfirming(id)
      return
    }
    setConfirming(null)
    try {
      await agentService.deleteConversation(id)
      if (id === activeId) onRemoved?.()
      await load()
    } catch {
      setFailed(true)
    }
  }

  async function open(id) {
    setFailed(false)
    try {
      onOpen(await agentService.conversation(id))
    } catch {
      setFailed(true)
    }
  }

  const tabClass = (name) =>
    `rounded-full px-3 py-1 text-xs ${tab === name ? "bg-surface-2 text-text" : "text-text-muted hover:text-text"}`

  return (
    <section aria-label={c.history} className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => { setTab("active"); onNew() }} disabled={disabled}
          className="inline-flex items-center gap-1.5 rounded bg-accent px-2.5 py-1.5 text-xs font-semibold text-black disabled:opacity-60 max-sm:min-h-10">
          <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" /> {c.newChat}
        </button>
        <div className="ms-auto flex gap-1" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "active"} className={tabClass("active")} onClick={() => setTab("active")}>
            {c.historyActive}
          </button>
          <button type="button" role="tab" aria-selected={tab === "archived"} className={tabClass("archived")} onClick={() => setTab("archived")}>
            {c.historyArchived}
          </button>
        </div>
      </div>
      <p className="text-[11px] text-text-faint">{c.historyHint(max)}</p>
      {failed ? <p role="alert" className="text-xs text-rose-300">{c.historyFailed}</p> : null}
      {items && items.length === 0 ? <p className="text-xs text-text-muted">{c.historyEmpty}</p> : null}
      <ul className="flex max-h-72 flex-col divide-y divide-border overflow-y-auto">
        {(items ?? []).map((item) => (
          <li key={item.id} className={`flex items-center gap-2 py-1.5 ${item.id === activeId ? "text-accent" : ""}`}>
            <button type="button" onClick={() => open(item.id)} disabled={disabled}
              className="min-w-0 flex-1 text-start max-sm:min-h-10" aria-current={item.id === activeId ? "true" : undefined}>
              <span className="block truncate text-sm text-text" dir="auto">{item.pinned ? "📌 " : ""}{item.title}</span>
              <span className="block text-[11px] text-text-faint">{formatDate(item.updated_at, lang)}</span>
            </button>
            {tab === "active" ? (
              <IconButton label={item.pinned ? c.unpin : c.pin} onClick={() => patch(item.id, { pinned: !item.pinned })}>
                {item.pinned ? <PinOff className="h-3.5 w-3.5" aria-hidden="true" /> : <Pin className="h-3.5 w-3.5" aria-hidden="true" />}
              </IconButton>
            ) : null}
            <IconButton label={tab === "active" ? c.archive : c.restore} onClick={() => patch(item.id, { archived: tab === "active" })}>
              {tab === "active" ? <Archive className="h-3.5 w-3.5" aria-hidden="true" /> : <ArchiveRestore className="h-3.5 w-3.5" aria-hidden="true" />}
            </IconButton>
            <IconButton label={confirming === item.id ? c.confirmRemove : c.remove} onClick={() => remove(item.id)} danger={confirming === item.id}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {confirming === item.id ? <span className="ms-1 text-[11px]">{c.confirmRemove}</span> : null}
            </IconButton>
          </li>
        ))}
      </ul>
    </section>
  )
}

function IconButton({ label, onClick, danger = false, children }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label}
      className={`inline-flex items-center rounded p-1.5 hover:bg-surface-2 max-sm:min-h-10 max-sm:min-w-10 max-sm:justify-center ${danger ? "text-rose-300" : "text-text-muted"}`}>
      {children}
    </button>
  )
}

export default ConversationHistory
