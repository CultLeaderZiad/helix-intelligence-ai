import { useEffect, useRef, useState } from "react"
import { Keyboard } from "lucide-react"
import { useW92Copy } from "@/i18n/w9_2Product"

function isTyping(target) {
  if (!target || !(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable
}

/**
 * W9-2 (D9): j/k move through the shown results, s saves the selected ad,
 * o opens it in the Ad Library, ? toggles the help. Ignored while typing or
 * with Ctrl/Meta/Alt held, so browser and form shortcuts still work.
 * @param {{enabled: boolean, items: Array<{id: string}>, selectedId: string|null, onSelect: (id: string) => void, onSave: (item: object) => void, onOpen: (item: object) => void, onToggleHelp: () => void}} opts
 */
export function useResultShortcuts({ enabled, items, selectedId, onSelect, onSave, onOpen, onToggleHelp }) {
  const latest = useRef({ items, selectedId, onSelect, onSave, onOpen, onToggleHelp })
  latest.current = { items, selectedId, onSelect, onSave, onOpen, onToggleHelp }

  useEffect(() => {
    if (!enabled) return undefined
    function onKey(event) {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return
      const { items: list, selectedId: sel, onSelect: select, onSave: save, onOpen: open, onToggleHelp: help } = latest.current
      const key = event.key
      if (key === "?") {
        event.preventDefault()
        help()
        return
      }
      if (!list.length) return
      const index = list.findIndex((i) => i.id === sel)
      if (key === "j" || key === "k") {
        event.preventDefault()
        const next = key === "j"
          ? list[index < 0 ? 0 : Math.min(index + 1, list.length - 1)]
          : list[index < 0 ? 0 : Math.max(index - 1, 0)]
        select(next.id)
        return
      }
      const current = index >= 0 ? list[index] : null
      if (!current) return
      if (key === "s") {
        event.preventDefault()
        save(current)
      } else if (key === "o") {
        event.preventDefault()
        open(current)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled])
}

/** The small "?" button and the list of shortcuts it shows. */
export function ShortcutHelp({ open, onToggle }) {
  const w = useW92Copy()
  const ref = useRef(null)
  const [id] = useState(() => `shortcut-help-${Math.random().toString(36).slice(2, 8)}`)
  const rows = [
    ["j", w.shortcutNext],
    ["k", w.shortcutPrev],
    ["s", w.shortcutSave],
    ["o", w.shortcutOpen],
    ["?", w.shortcutHelp],
  ]
  return (
    <div className="relative inline-block" ref={ref}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={id}
        aria-label={w.shortcutsButton}
        title={w.shortcutsButton}
        className="flex h-6 items-center gap-1 rounded border border-border px-1.5 text-[11px] text-text-muted hover:text-text"
      >
        <Keyboard className="h-3.5 w-3.5" aria-hidden="true" />?
      </button>
      {open ? (
        <div id={id} role="dialog" aria-label={w.shortcutsTitle} className="absolute bottom-full end-0 z-30 mb-1 w-64 rounded-lg border border-border bg-surface p-3 text-xs shadow-xl">
          <p className="mb-2 font-semibold text-text">{w.shortcutsTitle}</p>
          <dl className="space-y-1">
            {rows.map(([k, label]) => (
              <div key={k} className="flex items-center gap-2">
                <dt><kbd className="rounded border border-border bg-surface-2 px-1.5 font-mono">{k}</kbd></dt>
                <dd className="text-text-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </div>
  )
}
