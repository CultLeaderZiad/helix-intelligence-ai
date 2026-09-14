import React, { useState, useEffect, useMemo } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { 
  BookOpen, 
  Code2, 
  Search, 
  ChevronRight, 
  Menu, 
  X, 
  ExternalLink, 
  ArrowLeft, 
  ArrowRight,
  Sparkles,
  Layers,
  Terminal,
  Clock,
  CheckCircle2,
  FileText
} from 'lucide-react'
import { DOCS_REGISTRY, searchDocs, getAdjacentDocs } from './docsData'
import { slugify } from './MarkdownRenderer'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'

export function DocsLayout({ activeDoc, children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeHeading, setActiveHeading] = useState('')

  // Determine current active section: 'user-guide' or 'api-reference'
  const activeSectionKey = useMemo(() => {
    if (location.pathname.includes('/docs/api-reference')) return 'api-reference'
    if (location.pathname.includes('/docs/user-guide')) return 'user-guide'
    return activeDoc?.section || 'user-guide'
  }, [location.pathname, activeDoc])

  const currentSectionConfig = DOCS_REGISTRY.find((s) => s.section === activeSectionKey) || DOCS_REGISTRY[0]

  // Extract table of contents from activeDoc content
  const tableOfContents = useMemo(() => {
    if (!activeDoc?.content) return []
    const lines = activeDoc.content.split('\n')
    const headings = []
    lines.forEach((line) => {
      if (line.startsWith('## ')) {
        const text = line.replace(/^##\s+/, '').trim()
        headings.push({ level: 2, text, id: slugify(text) })
      } else if (line.startsWith('### ')) {
        const text = line.replace(/^###\s+/, '').trim()
        headings.push({ level: 3, text, id: slugify(text) })
      }
    })
    return headings
  }, [activeDoc?.content])

  // Track active heading on scroll
  useEffect(() => {
    const handleScroll = () => {
      const headingElements = tableOfContents
        .map((h) => document.getElementById(h.id))
        .filter(Boolean)

      const scrollPosition = window.scrollY + 120

      for (let i = headingElements.length - 1; i >= 0; i--) {
        const el = headingElements[i]
        if (el.offsetTop <= scrollPosition) {
          setActiveHeading(el.id)
          return
        }
      }
      if (headingElements.length > 0 && window.scrollY < 100) {
        setActiveHeading(headingElements[0].id)
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [tableOfContents])

  // Adjacent docs for bottom pagination
  const adjacent = useMemo(() => {
    if (!activeDoc) return { prev: null, next: null }
    return getAdjacentDocs(activeDoc.section, activeDoc.slug)
  }, [activeDoc])

  // Instant search results
  const searchResults = useMemo(() => searchDocs(searchQuery), [searchQuery])

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col font-sans selection:bg-accent selection:text-black">
      {/* 1. TOP HEADER (GitLab Docs Shell Inspired) */}
      <header className="sticky top-0 z-40 border-b border-border bg-surface/90 backdrop-blur-md px-4 lg:px-6 h-14 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-1.5 rounded-md hover:bg-surface-2 text-text-muted hover:text-text"
            aria-label="Toggle Navigation"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <Link to="/" className="flex items-center gap-2 group">
            <img src="/brand/helix-mark.svg" alt="Helix" className="h-5 w-5 rounded-[3px] object-contain" />
            <span className="font-mono text-sm font-bold tracking-tight text-text group-hover:text-accent transition-colors">
              Helix <span className="text-text-muted font-normal">Docs</span>
            </span>
          </Link>

          <span className="hidden sm:inline-block text-border font-mono text-xs">/</span>

          {/* Section Audience Switcher Tabs in Top Nav */}
          <div className="hidden sm:flex items-center rounded-md border border-border bg-surface-2 p-0.5">
            <Link
              to="/docs/user-guide/quickstart-account-and-trial"
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                activeSectionKey === 'user-guide'
                  ? 'bg-surface text-text shadow-xs font-semibold'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              <BookOpen className="h-3.5 w-3.5 text-accent" />
              <span>User Guide</span>
            </Link>
            <Link
              to="/docs/api-reference/authentication"
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                activeSectionKey === 'api-reference'
                  ? 'bg-surface text-text shadow-xs font-semibold'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              <Code2 className="h-3.5 w-3.5 text-accent" />
              <span>API Reference</span>
            </Link>
          </div>
        </div>

        {/* Global Live Search Bar */}
        <div className="flex-1 max-w-md relative hidden md:block">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-text-faint" />
            <input
              type="text"
              placeholder="Search documentation, guides & API..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-xs bg-surface-2 border border-border rounded-md text-text placeholder:text-text-faint focus:outline-none focus:border-accent/70 transition-colors"
            />
          </div>

          {/* Search Dropdown Modal */}
          {searchQuery && (
            <div className="absolute top-10 left-0 right-0 bg-surface border border-border rounded-md shadow-xl overflow-hidden z-50 divide-y divide-border/60 max-h-96 overflow-y-auto">
              <div className="px-3 py-1.5 bg-surface-2 font-mono text-[10px] text-text-faint uppercase tracking-wider flex justify-between">
                <span>Search Results ({searchResults.length})</span>
                <button onClick={() => setSearchQuery('')} className="hover:text-text">Clear</button>
              </div>
              {searchResults.length === 0 ? (
                <div className="p-4 text-center text-xs text-text-muted">
                  No matching documentation found for "{searchQuery}".
                </div>
              ) : (
                searchResults.map((result) => (
                  <Link
                    key={`${result.section}-${result.slug}`}
                    to={`/docs/${result.section}/${result.slug}`}
                    onClick={() => setSearchQuery('')}
                    className="block p-3 hover:bg-surface-2 transition-colors text-left"
                  >
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-accent">
                        {result.sectionLabel} · {result.groupTitle}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-text">{result.title}</div>
                    <div className="text-[11px] text-text-muted truncate mt-0.5">{result.description}</div>
                  </Link>
                ))
              )}
            </div>
          )}
        </div>

        {/* Action links */}
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <Link
            to="/discover"
            className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-medium border border-border bg-surface-2 hover:bg-surface-3 text-text transition-colors"
          >
            <span>Open Console</span>
            <ExternalLink className="h-3 w-3 text-text-faint" />
          </Link>
        </div>
      </header>

      {/* 2. BODY LAYOUT (Left-Nav + Main Content + Right TOC) */}
      <div className="flex-1 flex w-full max-w-[1520px] mx-auto">
        {/* LEFT NAVIGATION SIDEBAR */}
        <aside
          className={`fixed inset-y-14 left-0 z-30 w-72 border-r border-border bg-surface flex flex-col transition-transform duration-200 lg:static lg:w-64 lg:shrink-0 ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
        >
          {/* Section audience switcher on mobile */}
          <div className="p-3 border-b border-border sm:hidden flex flex-col gap-1.5">
            <span className="font-mono text-[10px] text-text-faint uppercase tracking-wider">Documentation Mode</span>
            <div className="grid grid-cols-2 gap-1 rounded bg-surface-2 p-0.5 border border-border">
              <Link
                to="/docs/user-guide/quickstart-account-and-trial"
                className={`py-1 text-center text-xs font-medium rounded ${
                  activeSectionKey === 'user-guide' ? 'bg-surface text-text font-semibold' : 'text-text-muted'
                }`}
              >
                User Guide
              </Link>
              <Link
                to="/docs/api-reference/authentication"
                className={`py-1 text-center text-xs font-medium rounded ${
                  activeSectionKey === 'api-reference' ? 'bg-surface text-text font-semibold' : 'text-text-muted'
                }`}
              >
                API Reference
              </Link>
            </div>
          </div>

          {/* Section Title & Description */}
          <div className="px-4 py-3 border-b border-border/70">
            <div className="flex items-center gap-2">
              {activeSectionKey === 'user-guide' ? (
                <BookOpen className="h-4 w-4 text-accent" />
              ) : (
                <Terminal className="h-4 w-4 text-accent" />
              )}
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-text">
                {currentSectionConfig.sectionLabel}
              </h2>
            </div>
            <p className="text-[11px] text-text-faint leading-relaxed mt-1">
              {currentSectionConfig.audience}
            </p>
          </div>

          {/* Navigation Links Tree */}
          <nav className="flex-1 overflow-y-auto p-3 space-y-5 scrollbar-thin">
            {currentSectionConfig.groups.map((group) => (
              <div key={group.groupTitle} className="space-y-1">
                <p className="px-2 font-mono text-[10px] font-bold uppercase tracking-wider text-text-faint">
                  {group.groupTitle}
                </p>
                <ul className="space-y-0.5">
                  {group.items.map((item) => {
                    const to = `/docs/${activeSectionKey}/${item.slug}`
                    const isActive = activeDoc?.slug === item.slug && activeDoc?.section === activeSectionKey
                    return (
                      <li key={item.slug}>
                        <NavLink
                          to={to}
                          className={`group flex items-center justify-between px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
                            isActive
                              ? 'bg-surface-2 text-accent font-semibold border-l-2 border-accent pl-2.5 shadow-2xs'
                              : 'text-text-muted hover:bg-surface-2/60 hover:text-text'
                          }`}
                        >
                          <span className="truncate">{item.title}</span>
                          {isActive && <ChevronRight className="h-3 w-3 text-accent shrink-0" />}
                        </NavLink>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
          </nav>

          {/* Bottom helper card */}
          <div className="p-3 border-t border-border bg-surface-2/40">
            <div className="p-2.5 rounded border border-border/80 bg-surface text-[11px] text-text-muted">
              <span className="font-mono text-[10px] text-accent font-semibold uppercase block mb-1">
                Static Git Docs
              </span>
              Built with zero runtime CMS. Versioned in git alongside the application code.
            </div>
          </div>
        </aside>

        {/* Mobile backdrop overlay */}
        {mobileMenuOpen && (
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 z-20 bg-black/60 backdrop-blur-xs lg:hidden"
          />
        )}

        {/* CENTER CONTENT VIEW */}
        <main className="flex-1 min-w-0 px-4 py-8 lg:px-10 max-w-4xl">
          {/* Breadcrumb row */}
          {activeDoc && (
            <div className="flex items-center gap-1.5 text-xs font-mono text-text-faint mb-6">
              <Link to="/docs" className="hover:text-text transition-colors">Docs</Link>
              <ChevronRight className="h-3 w-3" />
              <Link to={`/docs/${activeDoc.section}/${activeDoc.slug}`} className="text-text-muted hover:text-text">
                {activeDoc.sectionLabel}
              </Link>
              <ChevronRight className="h-3 w-3" />
              <span className="text-accent truncate">{activeDoc.title}</span>

              <div className="ml-auto flex items-center gap-1.5 text-[11px] text-text-faint">
                <Clock className="h-3 w-3" />
                <span>{activeDoc.readTime} read</span>
              </div>
            </div>
          )}

          {/* Render article children */}
          <article className="min-w-0">{children}</article>

          {/* Bottom Previous / Next Article Pagination */}
          {activeDoc && (
            <div className="mt-12 pt-6 border-t border-border flex items-center justify-between gap-4">
              {adjacent.prev ? (
                <Link
                  to={`/docs/${adjacent.prev.section}/${adjacent.prev.slug}`}
                  className="group flex flex-col items-start p-3 rounded-md border border-border bg-surface hover:bg-surface-2 transition-colors max-w-[45%]"
                >
                  <span className="flex items-center gap-1 text-[11px] font-mono text-text-faint group-hover:text-accent">
                    <ArrowLeft className="h-3 w-3" />
                    Previous
                  </span>
                  <span className="text-xs font-medium text-text mt-1 truncate w-full text-left">
                    {adjacent.prev.title}
                  </span>
                </Link>
              ) : <div />}

              {adjacent.next && (
                <Link
                  to={`/docs/${adjacent.next.section}/${adjacent.next.slug}`}
                  className="group flex flex-col items-end p-3 rounded-md border border-border bg-surface hover:bg-surface-2 transition-colors max-w-[45%] text-right"
                >
                  <span className="flex items-center gap-1 text-[11px] font-mono text-text-faint group-hover:text-accent">
                    Next
                    <ArrowRight className="h-3 w-3" />
                  </span>
                  <span className="text-xs font-medium text-text mt-1 truncate w-full text-right">
                    {adjacent.next.title}
                  </span>
                </Link>
              )}
            </div>
          )}
        </main>

        {/* RIGHT RAIL: ON THIS PAGE (TOC) */}
        {tableOfContents.length > 0 && (
          <aside className="hidden xl:block w-56 shrink-0 py-8 px-4 border-l border-border/70 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto">
            <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-faint mb-3">
              On This Page
            </p>
            <ul className="space-y-1 text-xs">
              {tableOfContents.map((heading) => {
                const isActive = activeHeading === heading.id
                return (
                  <li
                    key={heading.id}
                    className={heading.level === 3 ? 'pl-2.5' : ''}
                  >
                    <a
                      href={`#${heading.id}`}
                      className={`block py-1 leading-snug transition-colors truncate ${
                        isActive
                          ? 'text-accent font-medium'
                          : 'text-text-muted hover:text-text'
                      }`}
                    >
                      {heading.text}
                    </a>
                  </li>
                )
              })}
            </ul>

            <div className="mt-8 pt-4 border-t border-border/60">
              <a
                href="#top"
                onClick={(e) => {
                  e.preventDefault()
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                className="text-[11px] font-mono text-text-faint hover:text-accent transition-colors"
              >
                ↑ Back to top
              </a>
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}
