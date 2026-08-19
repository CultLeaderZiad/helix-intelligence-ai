import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { NAV_SECTIONS } from "./navigation"
import { KeyHint } from "@/components/ui/KeyHint"

/**
 * ⌘K palette. Real keyboard navigation: arrows move, Enter commits,
 * Escape closes, focus is trapped to the input. Not a decorative shell.
 */
export function CommandBar({ open, onClose }) {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [query, setQuery] = useState("")
  const [cursor, setCursor] = useState(0)

  const commands = useMemo(
    () =>
      NAV_SECTIONS.map((s) => ({
        id: s.key,
        label: `Go to ${s.label}`,
        hint: s.status === "pending" ? "no source" : "live",
        run: () => navigate(s.path),
      })),
    [navigate],
  )

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return commands
    return commands.filter((c) => c.label.toLowerCase().includes(needle))
  }, [commands, query])

  useEffect(() => {
    if (open) {
      setQuery("")
      setCursor(0)
      // Focus after paint so the browser does not scroll the panel.
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  useEffect(() => {
    setCursor(0)
  }, [query])

  if (!open) return null

  function handleKeyDown(event) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return

    if (event.key === "Escape") {
      onClose()
      return
    }
    if (event.key === "ArrowDown") {
      event.preventDefault()
      setCursor((c) => (matches.length ? (c + 1) % matches.length : 0))
      return
    }
    if (event.key === "ArrowUp") {
      event.preventDefault()
      setCursor((c) => (matches.length ? (c - 1 + matches.length) % matches.length : 0))
      return
    }
    if (event.key === "Enter") {
      event.preventDefault()
      const chosen = matches[cursor]
      if (chosen) {
        chosen.run()
        onClose()
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]">
      <button
        type="button"
        className="absolute inset-0 cursor-default bg-[#000]/70"
        onClick={onClose}
        aria-label="Close command palette"
      />
      <div
        className="relative w-full max-w-[440px] border border-border-strong bg-surface"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Run a command"
          className="h-10 w-full border-b border-border bg-transparent px-3 text-[13px] text-text placeholder:text-text-faint focus:outline-none"
        />

        <div className="max-h-[280px] overflow-y-auto p-1">
          {matches.length === 0 ? (
            <p className="px-2 py-6 text-center text-xs text-text-faint">
              No command matches that.
            </p>
          ) : (
            matches.map((c, i) => (
              <button
                key={c.id}
                type="button"
                onMouseEnter={() => setCursor(i)}
                onClick={() => {
                  c.run()
                  onClose()
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-sm px-2 py-[7px] text-left text-[13px] transition-colors",
                  i === cursor ? "bg-surface-3 text-text" : "text-text-muted",
                )}
              >
                <ChevronRight
                  className={cn(
                    "h-3 w-3 shrink-0",
                    i === cursor ? "text-accent" : "text-text-faint",
                  )}
                  aria-hidden="true"
                />
                <span className="flex-1 truncate">{c.label}</span>
                <span className="label-mono">{c.hint}</span>
              </button>
            ))
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-border px-3 py-1.5">
          <KeyHint>↑</KeyHint>
          <KeyHint>↓</KeyHint>
          <span className="label-mono">navigate</span>
          <KeyHint className="ml-2">↵</KeyHint>
          <span className="label-mono">run</span>
          <KeyHint className="ml-auto">esc</KeyHint>
        </div>
      </div>
    </div>
  )
}
