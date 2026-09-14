import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  BookOpen, 
  Code2, 
  Search, 
  ArrowRight, 
  Sparkles, 
  CheckCircle2, 
  ShieldCheck, 
  Terminal, 
  Zap,
  HelpCircle,
  ExternalLink
} from 'lucide-react'
import { PublicHeader } from '@/app/PublicHeader'
import { MarketingFooter } from '@/features/marketing/MarketingFooter'
import { DOCS_REGISTRY, searchDocs } from '@/features/docs/docsData'

export function DocsHomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()
  const searchResults = searchDocs(searchQuery)

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (searchResults.length > 0) {
      navigate(`/docs/${searchResults[0].section}/${searchResults[0].slug}`)
    }
  }

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col selection:bg-accent selection:text-black">
      <PublicHeader />

      <main className="flex-1">
        {/* 1. HERO SEARCH BANNER (GitLab Docs Style) */}
        <section className="relative overflow-hidden border-b border-border bg-gradient-to-b from-surface-2 via-surface to-bg py-20 px-4 sm:px-6">
          {/* Subtle background grid & glow */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f232812_1px,transparent_1px),linear-gradient(to_bottom,#1f232812_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

          <div className="relative mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-accent/30 bg-accent/5 text-[11px] font-mono text-accent uppercase tracking-wider mb-4">
              <Sparkles className="h-3 w-3" /> Helix Documentation System
            </span>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
              Find Helix answers fast
            </h1>
            <p className="mt-3 text-sm sm:text-base text-text-muted max-w-xl mx-auto leading-relaxed">
              Complete guides, core scoring concepts, and exact API references for competitive ad intelligence.
            </p>

            {/* Central Search Box */}
            <form onSubmit={handleSearchSubmit} className="mt-8 relative max-w-xl mx-auto">
              <div className="relative flex items-center">
                <Search className="absolute left-4 h-4 w-4 text-text-faint" />
                <input
                  type="text"
                  placeholder="Search topics, score formulas, API endpoints..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full h-12 pl-11 pr-24 rounded-lg bg-surface border border-border text-sm text-text placeholder:text-text-faint shadow-lg focus:outline-none focus:border-accent transition-colors font-sans"
                />
                <button
                  type="submit"
                  className="absolute right-2 px-3 py-1.5 rounded-md bg-accent text-black text-xs font-mono font-bold hover:bg-accent-bright transition-colors"
                >
                  Search
                </button>
              </div>

              {/* Instant Results Popup */}
              {searchQuery && (
                <div className="absolute top-14 left-0 right-0 bg-surface border border-border rounded-lg shadow-2xl overflow-hidden z-50 text-left divide-y divide-border/60 max-h-80 overflow-y-auto">
                  {searchResults.length === 0 ? (
                    <div className="p-4 text-center text-xs text-text-muted">
                      No matching documents found for "{searchQuery}".
                    </div>
                  ) : (
                    searchResults.map((r) => (
                      <Link
                        key={`${r.section}-${r.slug}`}
                        to={`/docs/${r.section}/${r.slug}`}
                        className="block p-3.5 hover:bg-surface-2 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] uppercase tracking-wider text-accent">
                            {r.sectionLabel}
                          </span>
                          <span className="text-[10px] text-text-faint">· {r.groupTitle}</span>
                        </div>
                        <div className="text-sm font-medium text-text mt-0.5">{r.title}</div>
                        <div className="text-xs text-text-muted truncate mt-0.5">{r.description}</div>
                      </Link>
                    ))
                  )}
                </div>
              )}
            </form>

            {/* Quick Access Topic Pills */}
            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="text-text-faint font-mono text-[11px]">Popular:</span>
              {[
                { label: '5-Min Quick Start', to: '/docs/user-guide/quickstart-account-and-trial' },
                { label: 'Scoring Formulas', to: '/docs/user-guide/concept-scoring-system' },
                { label: 'Estimated vs Real Data', to: '/docs/user-guide/concept-estimated-vs-real-data' },
                { label: 'API Authentication', to: '/docs/api-reference/authentication' },
                { label: 'Credit Costs Table', to: '/docs/api-reference/credit-costs-and-limits' },
                { label: 'Discover API', to: '/docs/api-reference/endpoint-discover' },
              ].map((pill) => (
                <Link
                  key={pill.label}
                  to={pill.to}
                  className="px-2.5 py-1 rounded-md border border-border bg-surface hover:border-accent/50 text-text-muted hover:text-text transition-colors font-mono text-[11px]"
                >
                  {pill.label}
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* 2. TWO DISTINCT AUDIENCE SECTIONS (Prompt Requirement) */}
        <section className="py-16 px-4 sm:px-6 max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* SECTION A CARD: USER GUIDE */}
            <div className="rounded-xl border border-border bg-surface p-6 sm:p-8 flex flex-col justify-between hover:border-border-strong transition-all group">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-text-faint px-2.5 py-1 rounded bg-surface-2 border border-border">
                    Section A
                  </span>
                </div>

                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-text group-hover:text-accent transition-colors">
                  User Guide
                </h2>
                <p className="mt-2 text-sm text-text-muted leading-relaxed">
                  Plain-language guides for growth marketers and testers. Learn how to uncover winning angles, interpret hook scores, and remix ad patterns without touching code.
                </p>

                <div className="mt-6 space-y-2 border-t border-border pt-4">
                  <p className="font-mono text-[11px] font-semibold text-text uppercase tracking-wider">
                    Core Topics:
                  </p>
                  <ul className="space-y-1.5 text-xs text-text-muted">
                    <li>
                      <Link to="/docs/user-guide/quickstart-account-and-trial" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Quick Start: Signup to first insight in &lt;5 minutes
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-how-discover-works" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        How Discover Works &amp; Real Data Limits
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-scoring-system" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Hook, Clarity, Retention &amp; Composite Scores
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-estimated-vs-real-data" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Estimated vs. Real Data (Transparency Pledge)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-audience-simulation" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Audience Simulation Rehearsal (Not a Predictor)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/faq" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Frequently Asked Questions (FAQ)
                      </Link>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-border">
                <Link
                  to="/docs/user-guide/quickstart-account-and-trial"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-surface-2 hover:bg-surface-3 border border-border text-xs font-mono font-medium text-text hover:text-accent transition-colors w-full justify-center"
                >
                  <span>Explore User Guide</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>

            {/* SECTION B CARD: API REFERENCE */}
            <div className="rounded-xl border border-border bg-surface p-6 sm:p-8 flex flex-col justify-between hover:border-border-strong transition-all group">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                    <Code2 className="h-5 w-5" />
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-text-faint px-2.5 py-1 rounded bg-surface-2 border border-border">
                    Section B
                  </span>
                </div>

                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-text group-hover:text-accent transition-colors">
                  API Reference
                </h2>
                <p className="mt-2 text-sm text-text-muted leading-relaxed">
                  Technical documentation for developers and BYOK users. Exact request/response schemas matching live backend models with real credit economics.
                </p>

                <div className="mt-6 space-y-2 border-t border-border pt-4">
                  <p className="font-mono text-[11px] font-semibold text-text uppercase tracking-wider">
                    Core Endpoints:
                  </p>
                  <ul className="space-y-1.5 text-xs text-text-muted">
                    <li>
                      <Link to="/docs/api-reference/authentication" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Authentication: Key generation &amp; X-API-Key pattern
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/credit-costs-and-limits" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Credit Costs &amp; Limits (Synced with billing_service.py)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-discover" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Discover Jobs: Scrape dispatch &amp; status polling
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-creatives" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Creatives: Catalog queries, swipe files &amp; insights
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-media-generate" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Media Generation: Higgsfield AI image &amp; video rendering
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-monitors" className="hover:text-accent flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-accent" />
                        Monitors: Scheduled loops &amp; event webhooks
                      </Link>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-border">
                <Link
                  to="/docs/api-reference/authentication"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-surface-2 hover:bg-surface-3 border border-border text-xs font-mono font-medium text-text hover:text-accent transition-colors w-full justify-center"
                >
                  <span>Explore API Reference</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>

          </div>
        </section>

        {/* 3. TRUST & REPO INTEGRITY STRIP */}
        <section className="border-t border-border bg-surface-2/40 py-12 px-4 sm:px-6">
          <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-text-muted">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-6 w-6 text-accent shrink-0" />
              <div>
                <p className="font-medium text-text">Zero CMS Drift</p>
                <p className="text-[11px] text-text-faint">
                  Documentation is stored as static markdown in git, reviewed and committed with every codebase release.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-accent shrink-0" />
              <div>
                <p className="font-medium text-text">100% Pydantic Schema Fidelity</p>
                <p className="text-[11px] text-text-faint">
                  Endpoint schemas and credit costs match live backend models with zero fabricated examples.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  )
}
