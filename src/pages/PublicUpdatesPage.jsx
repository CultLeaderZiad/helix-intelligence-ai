import React, { useState, useEffect, useMemo } from "react"
import { PublicHeader } from "@/app/PublicHeader"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"
import { updatesService } from "@/services"
import {
  Clock,
  Tag,
  Search,
  ExternalLink,
  Sparkles,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight,
  BookOpen,
  X
} from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Formats a date into a clean YYYY-MM-DD or standard display date.
 */
function formatPublishDate(dateStr) {
  if (!dateStr) return "Recently"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return String(dateStr)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    const day = String(d.getDate()).padStart(2, "0")
    return `${year}-${month}-${day}`
  } catch {
    return String(dateStr)
  }
}

/**
 * Parses markdown text into styled React elements:
 * - Markdown links [text](url) and raw URLs
 * - Bold **text**
 * - Inline code `code`
 * - Headings starting with ### or emoji
 * - Bullet lists
 */
function RichUpdateBody({ text, linkUrl }) {
  if (!text) return null

  // Split lines
  const lines = text.split("\n")

  const renderFormattedLine = (line, lineIdx) => {
    const trimmed = line.trim()

    // Empty line
    if (!trimmed) {
      return <div key={lineIdx} className="h-3" />
    }

    // Subheading lines (### or lines with emojis as headings)
    if (trimmed.startsWith("### ") || trimmed.startsWith("## ")) {
      const headingContent = trimmed.replace(/^#+\s*/, "")
      return (
        <h4 key={lineIdx} className="text-sm sm:text-base font-semibold text-text mt-4 mb-1.5 flex items-center gap-2">
          {headingContent}
        </h4>
      )
    }

    // Bullet items
    const isBullet = trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")
    const rawContent = isBullet ? trimmed.replace(/^[•\-\*]\s+/, "") : trimmed

    // Helper to format inline tokens (bold, code, links)
    const formatInline = (content) => {
      // Regex matches:
      // 1. Markdown link: [text](url)
      // 2. Raw URL: (https?://[^\s]+)
      // 3. Bold: \*\*(.*?)\*\*
      // 4. Code: `(.*?)`
      const tokenRegex = /(\[[^\]]+\]\([^\)]+\)|https?:\/\/[^\s\)]+|\*\*[^*]+\*\*|`[^`]+`)/g
      const parts = content.split(tokenRegex)

      return parts.map((part, i) => {
        if (!part) return null

        // Markdown Link [text](url)
        const mdLinkMatch = part.match(/^\[([^\]]+)\]\(([^\)]+)\)$/)
        if (mdLinkMatch) {
          const [, label, href] = mdLinkMatch
          const isExternal = href.startsWith("http")
          return (
            <a
              key={i}
              href={href}
              target={isExternal ? "_blank" : undefined}
              rel={isExternal ? "noopener noreferrer" : undefined}
              className="text-accent underline decoration-accent/40 hover:decoration-accent transition-colors font-medium"
            >
              {label}
            </a>
          )
        }

        // Raw URL
        if (/^https?:\/\//.test(part)) {
          return (
            <a
              key={i}
              href={part}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline decoration-accent/40 hover:decoration-accent transition-colors font-medium break-all"
            >
              {part}
            </a>
          )
        }

        // Bold **text**
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="text-text font-semibold">
              {part.slice(2, -2)}
            </strong>
          )
        }

        // Inline Code `text`
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code key={i} className="bg-surface-elevated border border-border px-1.5 py-0.5 rounded font-mono text-[11px] text-accent">
              {part.slice(1, -1)}
            </code>
          )
        }

        return <span key={i}>{part}</span>
      })
    }

    if (isBullet) {
      return (
        <div key={lineIdx} className="flex items-start gap-2.5 my-1 pl-1 text-[13px] sm:text-sm text-text-muted leading-relaxed">
          <span className="text-accent select-none mt-1 text-xs">•</span>
          <div className="flex-1">{formatInline(rawContent)}</div>
        </div>
      )
    }

    return (
      <p key={lineIdx} className="text-[13px] sm:text-sm text-text-muted leading-relaxed my-1">
        {formatInline(rawContent)}
      </p>
    )
  }

  return (
    <div className="space-y-1 my-3">
      {lines.map((line, idx) => renderFormattedLine(line, idx))}

      {linkUrl && (
        <div className="mt-5 pt-4 border-t border-border/60">
          <a
            href={linkUrl}
            target={linkUrl.startsWith("http") ? "_blank" : undefined}
            rel={linkUrl.startsWith("http") ? "noopener noreferrer" : undefined}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-surface-elevated/70 border border-border hover:border-accent/50 text-xs font-mono text-accent transition-all group"
          >
            <BookOpen className="h-3.5 w-3.5 text-accent group-hover:scale-105 transition-transform" />
            <span>Documentation & Quick Start</span>
            <ExternalLink className="h-3 w-3 text-text-faint group-hover:text-accent ml-0.5" />
          </a>
        </div>
      )}
    </div>
  )
}

export function PublicUpdatesPage() {
  const [updates, setUpdates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("All")

  const fetchUpdates = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await updatesService.getPublishedUpdates()
      setUpdates(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || "Failed to load platform updates")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUpdates()
  }, [])

  // Extract unique categories from updates
  const categories = useMemo(() => {
    const set = new Set(["All"])
    updates.forEach((u) => {
      if (u.category && u.category.trim()) {
        set.add(u.category.trim())
      }
    })
    return Array.from(set)
  }, [updates])

  // Filter updates based on search query and category
  const filteredUpdates = useMemo(() => {
    return updates.filter((u) => {
      const matchesCategory =
        selectedCategory === "All" ||
        (u.category && u.category.toLowerCase() === selectedCategory.toLowerCase())

      if (!matchesCategory) return false

      if (!searchQuery.trim()) return true

      const q = searchQuery.toLowerCase()
      const titleMatch = u.title && u.title.toLowerCase().includes(q)
      const bodyMatch = u.body && u.body.toLowerCase().includes(q)
      const categoryMatch = u.category && u.category.toLowerCase().includes(q)
      return titleMatch || bodyMatch || categoryMatch
    })
  }, [updates, searchQuery, selectedCategory])

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-text selection:bg-accent selection:text-bg font-sans">
      {/* Main App Public Header */}
      <PublicHeader />

      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
        {/* Page Hero Header */}
        <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-14">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs font-mono mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Changelog & System Releases</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text">
            Platform Updates
          </h1>
          <p className="mt-3 text-sm sm:text-base text-text-muted leading-relaxed">
            Follow the latest engine releases, ad intelligence scrapers, AI model additions,
            and API features built for Helix Intelligence.
          </p>
        </div>

        {/* Search & Filter Toolbar (KIE-style) */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-8 bg-surface-2/60 backdrop-blur-md border border-border/80 p-3 rounded-2xl shadow-lg">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-faint" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for updates... (Press enter to search)"
              className="w-full pl-10 pr-9 py-2 rounded-xl bg-bg/80 border border-border/80 text-xs sm:text-sm text-text placeholder:text-text-faint focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-all font-sans"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-faint hover:text-text p-0.5"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Category Filter Pills / Dropdown */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {categories.map((cat) => {
              const isSelected = selectedCategory.toLowerCase() === cat.toLowerCase()
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition-all border",
                    isSelected
                      ? "bg-accent text-bg font-semibold border-accent shadow-sm"
                      : "bg-surface border-border text-text-muted hover:text-text hover:border-border-strong"
                  )}
                >
                  {cat}
                </button>
              )
            })}
          </div>
        </div>

        {/* Content Section */}
        {loading ? (
          <div className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-2xl border border-border/60 bg-surface/60 p-6 sm:p-8 space-y-4 animate-pulse"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 w-28 bg-surface-elevated rounded" />
                  <div className="h-5 w-20 bg-surface-elevated rounded-full" />
                </div>
                <div className="h-6 w-3/4 bg-surface-elevated rounded" />
                <div className="space-y-2 pt-2">
                  <div className="h-3.5 w-full bg-surface-elevated rounded" />
                  <div className="h-3.5 w-5/6 bg-surface-elevated rounded" />
                  <div className="h-3.5 w-2/3 bg-surface-elevated rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-8 text-center space-y-4">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={fetchUpdates}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-surface border border-border text-xs font-mono text-text hover:border-accent transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry loading updates</span>
            </button>
          </div>
        ) : filteredUpdates.length === 0 ? (
          <div className="rounded-2xl border border-border/80 bg-surface/40 p-12 text-center space-y-3">
            <p className="text-sm text-text-muted">
              No updates match your search criteria.
            </p>
            {(searchQuery || selectedCategory !== "All") && (
              <button
                onClick={() => {
                  setSearchQuery("")
                  setSelectedCategory("All")
                }}
                className="text-xs font-mono text-accent hover:underline inline-flex items-center gap-1"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-8">
            {filteredUpdates.map((item) => {
              const publishDate = formatPublishDate(item.starts_at || item.created_at)
              const category = item.category || "General API"

              return (
                <article
                  key={item.id}
                  className="group relative rounded-2xl border border-border/80 bg-surface/80 backdrop-blur-sm p-6 sm:p-8 hover:border-border-strong hover:bg-surface transition-all duration-200 shadow-xl"
                >
                  {/* Top Meta Line: Publish Date + Category Tag */}
                  <div className="flex items-center justify-between gap-4 mb-4">
                    <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
                      <Clock className="h-3.5 w-3.5 text-text-faint" />
                      <span>{publishDate}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-[11px] tracking-wide uppercase">
                        <Tag className="h-2.5 w-2.5" />
                        {category}
                      </span>
                    </div>
                  </div>

                  {/* Title */}
                  <h2 className="text-xl sm:text-2xl font-bold text-text tracking-tight group-hover:text-accent transition-colors">
                    {item.title}
                  </h2>

                  {/* Body Content with Rich Formatting & Links */}
                  <RichUpdateBody text={item.body} linkUrl={item.link_url} />
                </article>
              )
            })}
          </div>
        )}
      </main>

      {/* Main Marketing Footer */}
      <MarketingFooter />
    </div>
  )
}

export default PublicUpdatesPage
