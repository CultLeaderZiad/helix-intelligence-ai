import { useState } from "react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Field"
import { archiveService } from "@/services"
import { useW9Copy } from "@/i18n/w9Product"

function snippet(text, max = 160) {
  const value = (text || "").trim()
  return value.length > max ? `${value.slice(0, max)}…` : value
}

function day(iso) {
  return iso ? String(iso).slice(0, 10) : ""
}

/**
 * Search ads this workspace already has (archive + saved), Postgres full-text
 * on the server, EN and AR. Costs 0 Metapi records; results are real rows.
 */
export function ArchiveSearch() {
  const w9 = useW9Copy()
  const [q, setQ] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  async function run(event) {
    event.preventDefault()
    const needle = q.trim()
    if (!needle) return
    setLoading(true)
    setFailed(false)
    try {
      setResult(await archiveService.search(needle, { scope: "all", page_size: 20 }))
    } catch {
      setResult(null)
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }

  const archive = result?.archive?.items ?? []
  const saved = result?.saved?.items ?? []
  return (
    <section className="border-b border-border px-4 py-3 text-sm" aria-label={w9.archiveSearchLabel}>
      <form onSubmit={run} className="flex flex-wrap items-center gap-2" role="search">
        <label htmlFor="archive-search" className="font-medium">{w9.archiveSearchLabel}</label>
        <Input
          id="archive-search"
          type="search"
          dir="auto"
          value={q}
          maxLength={200}
          placeholder={w9.archiveSearchPlaceholder}
          onChange={(event) => setQ(event.target.value)}
          className="min-w-48 flex-1"
        />
        <Button type="submit" size="sm" disabled={loading || !q.trim()}>{w9.archiveSearchButton}</Button>
        {result ? <Button type="button" size="sm" variant="ghost" onClick={() => setResult(null)}>{w9.close}</Button> : null}
      </form>
      <p className="mt-1 text-xs text-text-faint">{w9.archiveSearchHint}</p>
      {failed ? <p role="alert" className="mt-2 text-danger">{w9.archiveSearchFailed}</p> : null}
      {result ? (
        <div className="mt-3 space-y-3" role="region" aria-live="polite">
          <p className="text-text-muted">
            {w9.archiveSearchCount(result.archive?.total ?? 0)}
            {result.saved ? ` · ${w9.savedSearchCount(result.saved.total ?? 0)}` : ""}
          </p>
          {archive.length === 0 && saved.length === 0 ? <p>{w9.archiveSearchEmpty(result.query)}</p> : null}
          <ul className="space-y-2">
            {archive.map((item) => (
              <li key={`a-${item.id}`} className="border border-border bg-surface p-3" dir="auto">
                <p className="font-medium">{item.brand_name || "—"}{item.headline ? ` · ${item.headline}` : ""}</p>
                {item.body ? <p className="text-text-muted">{snippet(item.body)}</p> : null}
                <p className="mt-1 text-xs text-text-faint">
                  {w9.archivedOn(day(item.archived_at))}
                  {item.permalink ? <> · <a href={item.permalink} target="_blank" rel="noreferrer noopener" className="underline">{w9.openAd}</a></> : null}
                </p>
              </li>
            ))}
            {saved.map((item) => (
              <li key={`s-${item.id}`} className="border border-border bg-surface p-3" dir="auto">
                <p className="font-medium">{item.brand_name || "—"}{item.headline ? ` · ${item.headline}` : ""}</p>
                {item.body ? <p className="text-text-muted">{snippet(item.body)}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

export default ArchiveSearch
