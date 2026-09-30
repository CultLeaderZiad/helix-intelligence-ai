import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Search, 
  BookOpen, 
  Code2, 
  ChevronRight, 
  X, 
  Clock, 
  FileText, 
  CornerDownLeft, 
  ArrowUpDown,
  Sparkles
} from 'lucide-react'
import { ALL_DOCS, DOCS_REGISTRY } from './docsData'
import { cn } from '@/lib/utils'

export function DocSearchModal({ open, onClose, initialSection = 'all' }) {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const resultsRef = useRef(null)
  const [query, setQuery] = useState('')
  const [sectionFilter, setSectionFilter] = useState(initialSection)
  const [cursor, setCursor] = useState(0)

  // Focus input when modal opens
  useEffect(() => {
    if (open) {
      setQuery('')
      setCursor(0)
      setSectionFilter(initialSection)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open, initialSection])

  // Filter and search documentation with snippet matching
  const searchResults = useMemo(() => {
    const q = query.trim().toLowerCase()
    let pool = ALL_DOCS
    if (sectionFilter !== 'all') {
      pool = pool.filter((d) => d.section === sectionFilter)
    }

    if (!q) {
      // When empty query, return top recommended/starter docs
      return pool.slice(0, 7).map((doc) => ({
        ...doc,
        snippet: doc.description,
        matchType: 'recommended'
      }))
    }

    const matches = []
    for (const doc of pool) {
      const titleLower = doc.title.toLowerCase()
      const descLower = doc.description.toLowerCase()
      const groupLower = doc.groupTitle.toLowerCase()
      const contentLower = doc.content.toLowerCase()

      let score = 0
      let matchType = 'content'
      let snippet = doc.description

      if (titleLower.includes(q)) {
        score += 100
        matchType = 'title'
      } else if (descLower.includes(q)) {
        score += 50
        matchType = 'description'
      } else if (groupLower.includes(q)) {
        score += 30
        matchType = 'category'
      } else if (contentLower.includes(q)) {
        score += 10
        matchType = 'content'

        // Extract a 120-character snippet around the first match
        const idx = contentLower.indexOf(q)
        const start = Math.max(0, idx - 40)
        const end = Math.min(doc.content.length, idx + q.length + 80)
        const rawSnippet = doc.content.slice(start, end).replace(/[#*`_]/g, '').trim()
        snippet = (start > 0 ? '…' : '') + rawSnippet + (end < doc.content.length ? '…' : '')
      }

      if (score > 0) {
        matches.push({ ...doc, score, matchType, snippet })
      }
    }

    return matches.sort((a, b) => b.score - a.score).slice(0, 15)
  }, [query, sectionFilter])

  // Reset cursor on query or section change
  useEffect(() => {
    setCursor(0)
  }, [query, sectionFilter])

  // Scroll active item into view
  useEffect(() => {
    if (!resultsRef.current) return
    const activeEl = resultsRef.current.querySelector(`[data-index="${cursor}"]`)
    if (activeEl) {
      activeEl.scrollIntoView({ block: 'nearest' })
    }
  }, [cursor])

  if (!open) return null

  const handleSelect = (doc) => {
    onClose()
    navigate(`/docs/${doc.section}/${doc.slug}`)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setCursor((c) => (searchResults.length ? (c + 1) % searchResults.length : 0))
      return
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setCursor((c) => (searchResults.length ? (c - 1 + searchResults.length) % searchResults.length : 0))
      return
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      if (searchResults[cursor]) {
        handleSelect(searchResults[cursor])
      }
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Search Documentation"
      className="fixed inset-0 z-50 flex items-start justify-center p-3 sm:p-6 md:pt-20 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-surface border border-border rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border bg-surface-2/60">
          <Search className="h-5 w-5 text-accent shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search docs, APIs, scoring models, CLI commands..."
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-faint focus:outline-none font-sans"
            aria-autocomplete="list"
            aria-controls="doc-search-results"
          />
          {query ? (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="p-1 rounded text-text-faint hover:text-text"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-text-muted bg-surface border border-border rounded">
              ESC
            </kbd>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border/70 bg-surface/50 text-xs overflow-x-auto">
          <span className="text-[11px] font-mono text-text-faint uppercase tracking-wider shrink-0 mr-1">
            Filter:
          </span>
          <button
            type="button"
            onClick={() => setSectionFilter('all')}
            className={cn(
              "px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0",
              sectionFilter === 'all'
                ? "bg-accent text-black font-semibold"
                : "bg-surface-2 text-text-muted hover:text-text border border-border"
            )}
          >
            All Docs
          </button>
          <button
            type="button"
            onClick={() => setSectionFilter('user-guide')}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0",
              sectionFilter === 'user-guide'
                ? "bg-accent text-black font-semibold"
                : "bg-surface-2 text-text-muted hover:text-text border border-border"
            )}
          >
            <BookOpen className="h-3 w-3" />
            User Guide
          </button>
          <button
            type="button"
            onClick={() => setSectionFilter('api-reference')}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0",
              sectionFilter === 'api-reference'
                ? "bg-accent text-black font-semibold"
                : "bg-surface-2 text-text-muted hover:text-text border border-border"
            )}
          >
            <Code2 className="h-3 w-3" />
            API Reference
          </button>
        </div>

        {/* Search Results List */}
        <div
          ref={resultsRef}
          id="doc-search-results"
          role="listbox"
          className="flex-1 overflow-y-auto divide-y divide-border/40 p-2"
        >
          {searchResults.length === 0 ? (
            <div className="py-12 px-4 text-center">
              <div className="inline-flex p-3 rounded-full bg-surface-2 text-text-muted mb-3 border border-border">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-text">No documentation found</h3>
              <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                No matching topics for "{query}". Try searching for concepts like "scoring", "authentication", "leadgen", or "webhooks".
              </p>
            </div>
          ) : (
            searchResults.map((item, idx) => {
              const active = idx === cursor
              const isApi = item.section === 'api-reference'
              return (
                <div
                  key={`${item.section}-${item.slug}`}
                  data-index={idx}
                  role="option"
                  aria-selected={active}
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setCursor(idx)}
                  className={cn(
                    "group relative p-3 rounded-lg cursor-pointer transition-colors text-left",
                    active ? "bg-surface-2 text-text" : "hover:bg-surface-2/60 text-text"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      {/* Section & Category Badge */}
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded",
                            isApi
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-accent/10 text-accent border border-accent/20"
                          )}
                        >
                          {isApi ? <Code2 className="h-2.5 w-2.5" /> : <BookOpen className="h-2.5 w-2.5" />}
                          {item.sectionLabel}
                        </span>
                        <span className="text-[11px] text-text-faint font-mono">
                          {item.groupTitle}
                        </span>
                        {item.readTime && (
                          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] text-text-muted font-mono ml-auto">
                            <Clock className="h-2.5 w-2.5" /> {item.readTime}
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <div className="text-sm font-semibold text-text flex items-center gap-2">
                        <span>{item.title}</span>
                      </div>

                      {/* Snippet / Description Preview */}
                      <div className="text-xs text-text-muted line-clamp-2 mt-1 leading-relaxed font-sans">
                        {item.snippet}
                      </div>
                    </div>

                    <div className={cn("shrink-0 pt-2 transition-opacity", active ? "opacity-100" : "opacity-0")}>
                      <CornerDownLeft className="h-4 w-4 text-accent" />
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer Navigation Bar */}
        <div className="px-4 py-2 border-t border-border bg-surface-2/70 flex flex-wrap items-center justify-between text-[11px] font-mono text-text-faint">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 bg-surface border border-border rounded text-[10px]">↑</kbd>
              <kbd className="px-1 py-0.5 bg-surface border border-border rounded text-[10px]">↓</kbd>
              <span>navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface border border-border rounded text-[10px]">↵</kbd>
              <span>select</span>
            </span>
          </div>
          <span className="text-text-muted">
            {searchResults.length} {searchResults.length === 1 ? 'doc' : 'docs'}
          </span>
        </div>
      </div>
    </div>
  )
}
