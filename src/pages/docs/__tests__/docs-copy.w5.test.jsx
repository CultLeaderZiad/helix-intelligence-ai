import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { LanguageProvider } from '@/context/LanguageContext'
import { w5AuthDocs } from '@/i18n/w5AuthDocs'
import { DocsHomePage } from '@/pages/docs/DocsHomePage'
import { DocsDetailPage } from '@/pages/docs/DocsDetailPage'
import { DocSearchModal } from '@/features/docs/DocSearchModal'
import { getDocsReferenceCopy } from '@/features/docs/docsReferenceCopy'

vi.mock('@/app/PublicHeader', () => ({ PublicHeader: () => null }))
vi.mock('@/features/marketing/MarketingFooter', () => ({ MarketingFooter: () => null }))
vi.mock('@/features/docs/DocsLayout', () => ({ DocsLayout: ({ children }) => <div>{children}</div> }))
vi.mock('@/features/docs/MarkdownRenderer', () => ({ MarkdownRenderer: () => <article>Documentation content</article> }))

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function renderWithLanguage(ui, lang, route = '/docs') {
  localStorage.setItem('helix_lang', lang)
  return render(
    <MemoryRouter initialEntries={[route]}>
      <LanguageProvider>
        <Routes>
          <Route path="/docs" element={ui} />
          <Route path="/docs/:section/:slug" element={<DocsDetailPage />} />
        </Routes>
      </LanguageProvider>
    </MemoryRouter>,
  )
}

it.each(['en', 'ar'])('shows honest localized docs landing copy in %s', (lang) => {
  const { container } = renderWithLanguage(<DocsHomePage />, lang)

  expect(screen.getByRole('heading', { name: w5AuthDocs[lang].docsHomeTitle })).toBeTruthy()
  expect(screen.getByText(getDocsReferenceCopy(lang).message)).toBeTruthy()
  expect(screen.getByText(w5AuthDocs[lang].docsAccessAnswer)).toBeTruthy()
  expect(container.textContent).not.toMatch(/7-day trial|100 credits|20 daily searches|credit costs table|real credit economics|100%.*fidelity/i)
  expect(document.documentElement.dir).toBe(lang === 'ar' ? 'rtl' : 'ltr')
})

it.each(['en', 'ar'])('marks documentation as reference material in %s', (lang) => {
  renderWithLanguage(
    <DocsDetailPage />,
    lang,
    '/docs/user-guide/quickstart-account-and-trial',
  )

  expect(screen.getByRole('note').textContent).toContain(getDocsReferenceCopy(lang).message)
  expect(screen.getByRole('note').textContent).toContain(getDocsReferenceCopy(lang).usage)
  if (lang === 'ar') {
    expect(screen.getByText(w5AuthDocs.ar.docsEnglishNotice)).toBeTruthy()
  }
})

it.each(['en', 'ar'])('localizes docs search controls in %s', (lang) => {
  localStorage.setItem('helix_lang', lang)
  vi.stubGlobal('requestAnimationFrame', (callback) => callback())
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: vi.fn(),
  })

  render(
    <MemoryRouter>
      <LanguageProvider>
        <DocSearchModal open onClose={vi.fn()} />
      </LanguageProvider>
    </MemoryRouter>,
  )

  expect(screen.getByRole('dialog', { name: w5AuthDocs[lang].docsSearchTitle })).toBeTruthy()
  expect(screen.getByPlaceholderText(w5AuthDocs[lang].docsSearchHint)).toBeTruthy()
  expect(screen.getByRole('button', { name: w5AuthDocs[lang].docsFilterGuide })).toBeTruthy()
  expect(screen.getByRole('note').textContent).toContain(getDocsReferenceCopy(lang).message)
})
