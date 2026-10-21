import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, ChevronDown, Code2, Search, ShieldCheck } from 'lucide-react'
import { PublicHeader } from '@/app/PublicHeader'
import { MarketingFooter } from '@/features/marketing/MarketingFooter'
import { DocSearchModal } from '@/features/docs/DocSearchModal'
import { getDocsReferenceCopy } from '@/features/docs/docsReferenceCopy'
import { ScrollToTopButton } from '@/components/ui/ScrollToTopButton'
import { SkipToContent } from '@/components/ui/SkipToContent'
import { useLanguage } from '@/context/LanguageContext'

const GUIDE_LINKS = [
  { label: 'docsQuickStart', to: '/docs/user-guide/quickstart-account-and-trial' },
  { label: 'docsHowDiscover', to: '/docs/user-guide/concept-how-discover-works' },
  { label: 'docsScoringLink', to: '/docs/user-guide/concept-scoring-system' },
  { label: 'docsEstimatedLink', to: '/docs/user-guide/concept-estimated-vs-real-data' },
  { label: 'docsFaqLink', to: '/docs/user-guide/faq' },
]

const API_LINKS = [
  { label: 'docsApiAuthLink', to: '/docs/api-reference/authentication' },
  { label: 'docsUsageLimits', to: '/docs/api-reference/credit-costs-and-limits' },
  { label: 'docsDiscoverJobs', to: '/docs/api-reference/endpoint-discover' },
]

const FAQ_KEYS = [
  ['docsAccessQuestion', 'docsAccessAnswer'],
  ['docsNoResultsQuestion', 'docsNoResultsAnswer'],
  ['docsDataQuestion', 'docsDataAnswer'],
  ['docsPaymentsQuestion', 'docsPaymentsAnswer'],
  ['docsSourcesQuestion', 'docsSourcesAnswer'],
]

function DocsLinkList({ links, t, direction }) {
  return (
    <ul className="mt-3 space-y-1 border-t border-border pt-3 text-sm text-text-muted">
      {links.map((item) => (
        <li key={item.to}>
          <Link to={item.to} className="inline-flex min-h-8 items-center gap-2 py-1 hover:text-accent">
            <ArrowRight className={`h-3.5 w-3.5 shrink-0 text-accent ${direction}`} aria-hidden="true" />
            <span>{t(item.label)}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export function DocsHomePage() {
  const [searchModalOpen, setSearchModalOpen] = useState(false)
  const [openFaqIndex, setOpenFaqIndex] = useState(0)
  const { lang, t } = useLanguage()
  const isArabic = lang === 'ar'
  const direction = isArabic ? 'rotate-180' : ''
  const referenceCopy = getDocsReferenceCopy(lang)

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchModalOpen((open) => !open)
      } else if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        event.preventDefault()
        setSearchModalOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div dir={isArabic ? 'rtl' : 'ltr'} className="flex min-h-screen flex-col bg-bg text-text selection:bg-accent selection:text-black">
      <SkipToContent targetId="main-content" />
      <PublicHeader />

      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        <section className="relative overflow-hidden border-b border-border bg-gradient-to-b from-surface-2 via-surface to-bg px-4 py-16 sm:px-6 sm:py-20">
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#1f232812_1px,transparent_1px),linear-gradient(to_bottom,#1f232812_1px,transparent_1px)] bg-[size:24px_24px]" />
          <div className="relative mx-auto max-w-3xl text-center">
            <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/5 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-accent">
              <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
              {t('docsHomeBadge')}
            </span>
            <h1 className="text-3xl font-extrabold tracking-tight text-text sm:text-5xl">
              {t('docsHomeTitle')}
            </h1>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-text-muted sm:text-base">
              {t('docsHomeDescription')}
            </p>

            <div className="relative mx-auto mt-8 max-w-xl">
              <button
                type="button"
                onClick={() => setSearchModalOpen(true)}
                className="group flex min-h-14 w-full items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 text-start text-sm text-text-muted shadow-xl transition-all hover:border-accent/50 hover:shadow-accent/5"
                aria-label={t('docsOpenSearch')}
              >
                <span className="flex min-w-0 items-center gap-3">
                  <Search className="h-4 w-4 shrink-0 text-text-faint transition-colors group-hover:text-accent" aria-hidden="true" />
                  <span className="truncate">{t('docsHomeSearch')}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <kbd className="hidden rounded border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-text-faint sm:inline-flex">
                    ⌘K
                  </kbd>
                  <span className="rounded-md bg-accent px-3 py-1.5 font-mono text-xs font-bold text-black transition-colors group-hover:bg-accent-bright">
                    {t('docsSearch')}
                  </span>
                </span>
              </button>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="font-mono text-[11px] text-text-faint">{t('docsPopular')}:</span>
              {[
                { label: 'docsQuickStart', to: '/docs/user-guide/quickstart-account-and-trial' },
                { label: 'docsHowDiscover', to: '/docs/user-guide/concept-how-discover-works' },
                { label: 'docsUsageLimits', to: '/docs/api-reference/credit-costs-and-limits' },
                { label: 'docsFaqLink', to: '/docs/user-guide/faq' },
              ].map((item) => (
                <Link key={item.to} to={item.to} className="rounded-md border border-border bg-surface px-2.5 py-1 font-mono text-[11px] text-text-muted transition-colors hover:border-accent/50 hover:text-text">
                  {t(item.label)}
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 pt-8 sm:px-6">
          <div role="note" className="flex gap-3 rounded-lg border border-border bg-surface-2/60 p-4 text-sm">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
            <div>
              <h2 className="font-semibold text-text">{referenceCopy.title}</h2>
              <p className="mt-1 leading-relaxed text-text-muted">{referenceCopy.message}</p>
              <p className="mt-1 leading-relaxed text-text-muted">{referenceCopy.usage}</p>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <section className="group flex flex-col rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong sm:p-8">
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-accent/20 bg-accent/10 text-accent">
                  <BookOpen className="h-5 w-5" aria-hidden="true" />
                </div>
                <span className="rounded border border-border bg-surface-2 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-text-faint">
                  {t('docsUserGuide')}
                </span>
              </div>
              <h2 className="mt-4 text-xl font-bold tracking-tight text-text transition-colors group-hover:text-accent sm:text-2xl">
                {t('docsUserGuide')}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-text-muted">{t('docsGuidePlainLanguage')}</p>
              <div className="mt-5">
                <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text">{t('docsCoreTopics')}</p>
                <DocsLinkList links={GUIDE_LINKS} t={t} direction={direction} />
              </div>
              <Link
                to="/docs/user-guide/quickstart-account-and-trial"
                className="mt-6 inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface-2 px-4 py-2 font-mono text-xs font-medium text-text transition-colors hover:bg-surface-3 hover:text-accent"
              >
                {t('docsExploreGuide')}
                <ArrowRight className={`h-3.5 w-3.5 ${direction}`} aria-hidden="true" />
              </Link>
            </section>

            <section className="group flex flex-col rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong sm:p-8">
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-accent/20 bg-accent/10 text-accent">
                  <Code2 className="h-5 w-5" aria-hidden="true" />
                </div>
                <span className="rounded border border-border bg-surface-2 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-text-faint">
                  {t('docsApiReference')}
                </span>
              </div>
              <h2 className="mt-4 text-xl font-bold tracking-tight text-text transition-colors group-hover:text-accent sm:text-2xl">
                {t('docsApiReference')}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-text-muted">{t('docsApiDescription')}</p>
              <p className="mt-3 text-xs leading-relaxed text-text-faint">{t('docsIntegrityDescription')}</p>
              <div className="mt-5">
                <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text">{t('docsCoreEndpoints')}</p>
                <DocsLinkList links={API_LINKS} t={t} direction={direction} />
              </div>
              <Link
                to="/docs/api-reference/authentication"
                className="mt-6 inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface-2 px-4 py-2 font-mono text-xs font-medium text-text transition-colors hover:bg-surface-3 hover:text-accent"
              >
                {t('docsExploreApi')}
                <ArrowRight className={`h-3.5 w-3.5 ${direction}`} aria-hidden="true" />
              </Link>
            </section>
          </div>
        </section>

        <section className="mx-auto max-w-4xl border-t border-border/70 px-4 py-12 sm:px-6 sm:py-16">
          <div className="mb-8 text-center">
            <h2 className="mt-4 text-2xl font-bold tracking-tight text-text sm:text-3xl">{t('docsFaqTitle')}</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm text-text-muted">{t('docsFaqDescription')}</p>
          </div>

          <div className="space-y-3">
            {FAQ_KEYS.map(([questionKey, answerKey], index) => {
              const isOpen = openFaqIndex === index
              const answerId = `docs-faq-answer-${index}`
              return (
                <div key={questionKey} className="overflow-hidden rounded-lg border border-border bg-surface transition-colors hover:border-border-strong">
                  <button
                    type="button"
                    onClick={() => setOpenFaqIndex(isOpen ? null : index)}
                    aria-expanded={isOpen}
                    aria-controls={answerId}
                    className="flex min-h-12 w-full items-center justify-between gap-3 px-5 py-4 text-start text-sm font-semibold text-text transition-colors hover:text-accent"
                  >
                    <span>{t(questionKey)}</span>
                    <ChevronDown className={`h-4 w-4 shrink-0 text-text-muted transition-transform ${isOpen ? 'rotate-180 text-accent' : ''}`} aria-hidden="true" />
                  </button>
                  {isOpen && (
                    <div id={answerId} className="border-t border-border/60 px-5 pb-4 pt-3 text-xs leading-relaxed text-text-muted sm:text-[13px]">
                      {t(answerKey)}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="mt-7 text-center">
            <Link to="/docs/user-guide/faq" className="inline-flex items-center gap-1.5 font-mono text-xs text-accent transition-colors hover:text-accent-bright">
              {t('docsViewAll')}
              <ArrowRight className={`h-3.5 w-3.5 ${direction}`} aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      <MarketingFooter />
      <ScrollToTopButton />
      <DocSearchModal open={searchModalOpen} onClose={() => setSearchModalOpen(false)} />
    </div>
  )
}
