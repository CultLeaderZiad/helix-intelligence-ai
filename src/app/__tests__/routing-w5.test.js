import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('W5 direct route loading', () => {
  it('proxies only the API path boundary, not /api-keys', () => {
    const config = readFileSync(new URL('../../../vite.config.js', import.meta.url), 'utf8')
    const pattern = config.match(/"(\^\/api[^"\n]+)":\s*\{/)?.[1]
    expect(pattern).toBeDefined()
    const proxy = new RegExp(pattern)
    expect(proxy.test('/api')).toBe(true)
    expect(proxy.test('/api/discovery/jobs')).toBe(true)
    expect(proxy.test('/api-keys')).toBe(false)
    expect(proxy.test('/api-docs')).toBe(false)
  })

  it('keeps Vercel SPA fallback for direct routes and asset paths', () => {
    const config = JSON.parse(readFileSync(new URL('../../../vercel.json', import.meta.url), 'utf8'))
    expect(config.rewrites.at(-1)).toEqual({ source: '/(.*)', destination: '/index.html' })
    expect(config.rewrites.some((route) => route.source === '/assets/:path*' && route.destination === '/assets/:path*')).toBe(true)
  })
})
