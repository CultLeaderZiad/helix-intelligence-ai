import React, { useState, useEffect } from 'react'
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
  ExternalLink,
  ChevronDown
} from 'lucide-react'
import { PublicHeader } from '@/app/PublicHeader'
import { MarketingFooter } from '@/features/marketing/MarketingFooter'
import { DOCS_REGISTRY } from '@/features/docs/docsData'
import { DocSearchModal } from '@/features/docs/DocSearchModal'
import { ScrollToTopButton } from '@/components/ui/ScrollToTopButton'
import { SkipToContent } from '@/components/ui/SkipToContent'

const CORE_FAQ_ITEMS = [
  {
    question: 'Why did my search return no results?',
    answer: 'Ad transparency libraries only catalog creatives actively running in recent weeks. If a competitor paused their campaigns, or if their ads run under a parent corporate entity or agency rather than their personal alias, queries may return empty. In transient upstream rate limit events, your search credits are automatically refunded.'
  },
  {
    question: 'What is the difference between estimated and reported data?',
    answer: 'Reported data is 100% factual public record: verbatim headlines, ad body text, video MP4s, thumbnail images, and first-seen timestamps. Estimated metrics (like reach brackets and spend estimates) are clearly demarcated with amber "(est)" badges so you always know what is directly reported versus modeled.'
  },
  {
    question: 'What happens when my 7-day trial ends?',
    answer: 'During your 7-day trial, you receive 100 credits and 20 daily searches. When 7 days elapse, your account enters Read-Only Mode. All previously discovered creatives and saved swipe files remain accessible. You are never automatically billed without explicitly choosing a plan.'
  },
  {
    question: 'Are credits refunded if a scrape job fails?',
    answer: 'Yes, 100%. If an ad-network timeout or transient provider disconnect occurs while processing your scrape or media generation, the billing engine immediately restores the deducted credits to your workspace balance. Helix never charges for incomplete jobs.'
  },
  {
    question: 'How do I translate foreign language ads into English?',
    answer: 'Helix automatically detects non-English copy across 40+ languages. When inspecting a creative in the Intelligence drawer or Intelligence page, use the language selector to instantly view an English translation of the headline, body copy, and call to action.'
  },
  {
    question: 'How does Helix prevent CMS documentation drift?',
    answer: 'Our documentation is stored as static markdown files committed to the repository alongside code. Each page’s "Last Updated" timestamp is dynamically extracted from actual git commit history during build time, ensuring 100% schema fidelity with backend Pydantic models.'
  }
]

export function DocsHomePage() {
  const [searchModalOpen, setSearchModalOpen] = useState(false)
  const [openFaqIndex, setOpenFaqIndex] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchModalOpen((v) => !v)
      } else if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        e.preventDefault()
        setSearchModalOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col selection:bg-accent selection:text-black">
      {/* Skip to Content for keyboard accessibility */}
      <SkipToContent targetId="main-content" />

      <PublicHeader />

      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
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

            {/* Central Search Box Trigger */}
            <div className="mt-8 relative max-w-xl mx-auto">
              <button
                type="button"
                onClick={() => setSearchModalOpen(true)}
                className="w-full h-13 pl-4 pr-3 rounded-lg bg-surface border border-border hover:border-accent/50 text-left text-sm text-text-muted shadow-xl hover:shadow-accent/5 transition-all flex items-center justify-between group cursor-pointer"
                aria-label="Open documentation search"
              >
                <div className="flex items-center gap-3">
                  <Search className="h-4 w-4 text-text-faint group-hover:text-accent transition-colors" />
                  <span className="text-text-faint group-hover:text-text-muted transition-colors">
                    Search topics, score formulas, API endpoints...
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-1 text-xs font-mono text-text-faint bg-surface-2 border border-border rounded shadow-2xs">
                    <span className="text-xs">⌘</span>K
                  </kbd>
                  <span className="px-3 py-1.5 rounded-md bg-accent text-black text-xs font-mono font-bold group-hover:bg-accent-bright transition-colors">
                    Search
                  </span>
                </div>
              </button>
            </div>

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
                  <ul className="space-y-1 text-xs text-text-muted">
                    <li>
                      <Link to="/docs/user-guide/quickstart-account-and-trial" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Quick Start: Signup to first insight in &lt;5 minutes
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-how-discover-works" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        How Discover Works &amp; Real Data Limits
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-scoring-system" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Hook, Clarity, Retention &amp; Composite Scores
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-estimated-vs-real-data" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Estimated vs. Real Data (Transparency Pledge)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/concept-audience-simulation" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Audience Simulation Rehearsal (Not a Predictor)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/user-guide/faq" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
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
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
            </div>

            {/* SECTION B CARD: API REFERENCE */}
            <div className="rounded-xl border border-border bg-surface p-6 sm:p-8 flex flex-col justify-between hover:border-border-strong transition-all group">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                    <Code2 className="h-5 w-5" aria-hidden="true" />
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
                  <ul className="space-y-1 text-xs text-text-muted">
                    <li>
                      <Link to="/docs/api-reference/authentication" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Authentication: Key generation &amp; X-API-Key pattern
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/credit-costs-and-limits" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Credit Costs &amp; Limits (Synced with billing_service.py)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-discover" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Discover Jobs: Scrape dispatch &amp; status polling
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-creatives" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Creatives: Catalog queries, swipe files &amp; insights
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-media-generate" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
                        Media Generation: AI image &amp; video rendering (Gemini)
                      </Link>
                    </li>
                    <li>
                      <Link to="/docs/api-reference/endpoint-monitors" className="hover:text-accent inline-flex items-center gap-1.5 py-1 min-h-[28px]">
                        <ArrowRight className="h-3 w-3 text-accent shrink-0" aria-hidden="true" />
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

        {/* 3. EXPANDABLE FAQ ACCORDION SECTION */}
        <section className="py-16 px-4 sm:px-6 max-w-4xl mx-auto border-t border-border/70">
          <div className="text-center mb-10">
            <span className="px-3 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-accent/10 text-accent border border-accent/20">
              Clear &amp; Transparent
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text mt-3">
              Frequently Asked Questions
            </h2>
            <p className="text-sm text-text-muted mt-2 max-w-xl mx-auto">
              Straight answers on data freshness, credit refunds, trial limits, and scoring formulas.
            </p>
          </div>

          <div className="space-y-3">
            {CORE_FAQ_ITEMS.map((item, idx) => {
              const isOpen = openFaqIndex === idx
              return (
                <div
                  key={idx}
                  className="rounded-lg border border-border bg-surface overflow-hidden transition-all duration-200 hover:border-border-strong"
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaqIndex(isOpen ? null : idx)}
                    aria-expanded={isOpen}
                    className="w-full text-left px-5 py-4 flex items-center justify-between gap-3 text-sm font-semibold text-text hover:text-accent transition-colors cursor-pointer select-none"
                  >
                    <span>{item.question}</span>
                    <ChevronDown
                      className={`h-4 w-4 shrink-0 text-text-muted transition-transform duration-200 ${
                        isOpen ? 'rotate-180 text-accent' : ''
                      }`}
                    />
                  </button>
                  {isOpen && (
                    <div className="px-5 pb-4 pt-1 border-t border-border/60 text-xs sm:text-[13px] text-text-muted leading-relaxed">
                      <p>{item.answer}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="mt-8 text-center">
            <Link
              to="/docs/user-guide/faq"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-accent hover:text-accent-bright transition-colors"
            >
              <span>Explore complete FAQ article in User Guide</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </section>

        {/* 4. TRUST & REPO INTEGRITY STRIP */}
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

      {/* Floating Scroll to Top */}
      <ScrollToTopButton />

      {/* Real Docs & API Reference Site Search Modal */}
      <DocSearchModal
        open={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
      />
    </div>
  )
}
