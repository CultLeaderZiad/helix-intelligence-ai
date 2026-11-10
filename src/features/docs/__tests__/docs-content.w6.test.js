import { describe, expect, it } from 'vitest'
import { ALL_DOCS, DOCS_REGISTRY, getDoc, searchDocs } from '../docsData'

describe('public documentation content', () => {
  it('loads every registered article from the public directories', () => {
    const registered = DOCS_REGISTRY.flatMap(section => section.groups.flatMap(group => group.items))
    expect(ALL_DOCS).toHaveLength(registered.length)
    for (const article of ALL_DOCS) {
      expect(article.file).toMatch(/^(user-guide|api-reference)\//)
      expect(article.content.trim().length).toBeGreaterThan(0)
      expect(getDoc(article.section, article.slug)).toBe(article)
    }
  })

  it('keeps article search available after narrowing the bundle inputs', () => {
    const results = searchDocs('Discover')
    expect(results.length).toBeGreaterThan(0)
    expect(results.every(article => article.content.length > 0)).toBe(true)
  })
})
