import { useEffect, useState } from "react"
import { BookOpen, Search } from "lucide-react"
import { request } from "@/services/http"
import { useLanguage } from "@/context/LanguageContext"

export const KNOWLEDGE_COPY = {
  en: {
    title: "Knowledge base",
    intro: "Guides written and kept up to date by the Helix team. Ask Helix reads the same articles.",
    search: "Search the articles",
    searchGo: "Search",
    empty: "No articles yet.",
    noResults: "No article matches that search.",
    failed: "Could not load the knowledge base. Try again.",
    back: "All articles",
    version: (v) => `Version ${v}`,
    updated: (d) => `Updated ${d}`,
  },
  ar: {
    title: "قاعدة المعرفة",
    intro: "أدلة يكتبها فريق Helix ويحدّثها باستمرار. ويقرأ Ask Helix نفس المقالات.",
    search: "ابحث في المقالات",
    searchGo: "بحث",
    empty: "لا توجد مقالات بعد.",
    noResults: "لا يوجد مقال يطابق هذا البحث.",
    failed: "تعذّر تحميل قاعدة المعرفة. أعد المحاولة.",
    back: "كل المقالات",
    version: (v) => `الإصدار ${v}`,
    updated: (d) => `آخر تحديث ${d}`,
  },
}

const get = (path, params) => request(`/knowledge-base${path}`, params ? { params } : {})

function day(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang === "ar" ? "ar" : "en", { year: "numeric", month: "short", day: "numeric" })
  } catch {
    return ""
  }
}

/** Read-only view of the enabled knowledge-base articles. Only admins can change them (in the admin console). */
export function KnowledgePage() {
  const { lang } = useLanguage()
  const c = lang === "ar" ? KNOWLEDGE_COPY.ar : KNOWLEDGE_COPY.en
  const [articles, setArticles] = useState(null)
  const [query, setQuery] = useState("")
  const [hits, setHits] = useState(null)
  const [open, setOpen] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let live = true
    get("").then((res) => live && setArticles(res?.items ?? [])).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [])

  async function runSearch(event) {
    event.preventDefault()
    setFailed(false)
    if (!query.trim()) return setHits(null)
    try {
      setHits((await get("/search", { q: query.trim() }))?.items ?? [])
    } catch {
      setFailed(true)
    }
  }

  async function read(id) {
    setFailed(false)
    try {
      setOpen(await get(`/${encodeURIComponent(id)}`))
    } catch {
      setFailed(true)
    }
  }

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-3xl flex-col gap-5 p-4 sm:p-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-semibold text-text">
          <BookOpen className="h-6 w-6 text-accent" aria-hidden="true" /> {c.title}
        </h1>
        <p className="mt-1 text-sm text-text-muted">{c.intro}</p>
      </header>

      {failed ? <p role="alert" className="text-sm text-rose-300">{c.failed}</p> : null}

      {open ? (
        <article className="flex flex-col gap-3">
          <button type="button" onClick={() => setOpen(null)} className="self-start text-xs text-accent hover:underline max-sm:min-h-10">
            ← {c.back}
          </button>
          <h2 className="text-xl font-semibold text-text" dir="auto">{open.title}</h2>
          <p className="text-xs text-text-faint">{c.version(open.version)} · {c.updated(day(open.updated_at, lang))}</p>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-text" dir="auto">{open.text}</div>
        </article>
      ) : (
        <>
          <form onSubmit={runSearch} role="search" className="flex gap-2">
            <label className="sr-only" htmlFor="kb-search">{c.search}</label>
            <input id="kb-search" value={query} onChange={(e) => { setQuery(e.target.value); if (!e.target.value) setHits(null) }}
              placeholder={c.search} maxLength={200}
              className="h-10 min-w-0 flex-1 rounded-sm border border-border bg-surface-2 px-3 text-base text-text placeholder:text-text-faint sm:h-8 sm:text-[13px]" />
            <button type="submit" className="inline-flex items-center gap-1.5 rounded bg-accent px-3 text-xs font-semibold text-black max-sm:min-h-10">
              <Search className="h-3.5 w-3.5" aria-hidden="true" /> {c.searchGo}
            </button>
          </form>

          {hits ? (
            hits.length === 0 ? <p className="text-sm text-text-muted">{c.noResults}</p> : (
              <ul className="flex flex-col divide-y divide-border">
                {hits.map((h, i) => (
                  <li key={`${h.document_id}-${i}`}>
                    <button type="button" onClick={() => read(h.document_id)} className="w-full py-2.5 text-start max-sm:min-h-10">
                      <span className="block text-sm font-medium text-text" dir="auto">{h.title}</span>
                      <span className="block text-xs text-text-muted" dir="auto">{h.snippet}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : articles && articles.length === 0 ? (
            <p className="text-sm text-text-muted">{c.empty}</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {(articles ?? []).map((a) => (
                <li key={a.id}>
                  <button type="button" onClick={() => read(a.id)} className="w-full py-2.5 text-start max-sm:min-h-10">
                    <span className="block text-sm font-medium text-text" dir="auto">{a.title}</span>
                    <span className="block text-xs text-text-faint">{c.version(a.version)} · {c.updated(day(a.updated_at, lang))}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

export default KnowledgePage
