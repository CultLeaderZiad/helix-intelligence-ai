import React from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { getMarkdownHeadings } from '../markdownHeadings'
import { DocsLayout } from '../DocsLayout'
import { MarkdownRenderer } from '../MarkdownRenderer'

vi.mock('@/context/LanguageContext', () => ({ useLanguage: () => ({ lang: 'en', isRtl: false, t: (key, fallback) => fallback || key, toggleLanguage: vi.fn() }) }))
vi.mock('@/hooks/useMediaQuery', () => ({ useIsBelowLg: () => true }))

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

const content = '# Monitor\n## Response\nExample\n## Response\nMore\n```md\n## Not a heading\n```'
function article() {
  vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} })
  const doc = { section: 'api-reference', slug: 'endpoint-monitors', title: 'Monitor', content, readTime: '4 min' }
  return render(<MemoryRouter initialEntries={['/docs/api-reference/endpoint-monitors']}><DocsLayout activeDoc={doc}><MarkdownRenderer content={content} /></DocsLayout></MemoryRouter>)
}

describe('documentation navigation', () => {
  it('generates unique anchors and excludes fenced examples', () => {
    expect(getMarkdownHeadings(content).map(heading => heading.id)).toEqual(['monitor', 'response', 'response-2'])
    expect(getMarkdownHeadings('## Response\n## Response-2\n## Response').map(heading => heading.id)).toEqual(['response', 'response-2', 'response-3'])
  })

  it('uses the same unique anchors in the article and contents list', () => {
    const errors = vi.spyOn(console, 'error')
    const { container } = article()
    expect([...container.querySelectorAll('article h2')].map(heading => heading.id)).toEqual(['response', 'response-2'])
    expect(screen.getAllByRole('button', { name: 'Response' })).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Not a heading' })).toBeNull()
    expect(errors).not.toHaveBeenCalled()
  })

  it('opens and closes the mobile drawer without retaining scroll lock', () => {
    article()
    const toggle = screen.getByRole('button', { name: 'Toggle navigation' })
    toggle.focus()
    fireEvent.click(toggle)
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(document.body.style.overflow).toBe('hidden')
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.body.style.overflow).toBe('')
    expect(document.activeElement).toBe(toggle)
  })
})
