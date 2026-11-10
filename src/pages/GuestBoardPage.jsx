import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ExternalLink, Link2Off } from "lucide-react"
import { boardService } from "@/services"
import { useW8Copy } from "@/i18n/w8Product"
import { useLanguage } from "@/context/LanguageContext"
import { formatDays } from "@/lib/format"
import { EmptyState, SkeletonRows } from "@/components/ui/States"

function formatDate(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang === "ar" ? "ar" : "en", { year: "numeric", month: "short", day: "numeric" })
  } catch {
    return iso
  }
}

/** Keep the capability URL out of Referer headers and search indexes. */
function useGuestPageMeta() {
  useEffect(() => {
    const added = [["referrer", "no-referrer"], ["robots", "noindex, nofollow"]].map(([name, content]) => {
      const meta = document.createElement("meta")
      meta.name = name
      meta.content = content
      document.head.append(meta)
      return meta
    })
    return () => added.forEach((meta) => meta.remove())
  }, [])
}

function GuestAd({ ad, c }) {
  const image = ad.thumbnail_url || (ad.format === "image" ? ad.media_url : null)
  return (
    <article className="flex flex-col overflow-hidden rounded-md border border-border bg-surface">
      {image ? (
        <div className="flex h-44 items-center justify-center overflow-hidden border-b border-border bg-surface-2">
          <img src={image} alt={ad.headline || ad.brand_name || ""} className="h-full w-full object-cover" loading="lazy" referrerPolicy="no-referrer" />
        </div>
      ) : null}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <span className="label-mono text-text-faint">{ad.brand_name || "—"} · {ad.platform}</span>
        {ad.headline ? <h3 className="text-sm font-semibold text-text">{ad.headline}</h3> : null}
        {ad.body ? <p className="line-clamp-5 text-xs leading-relaxed text-text-muted">{ad.body}</p> : null}
        <dl className="mt-auto flex flex-wrap gap-x-5 gap-y-1 border-t border-border pt-2 font-mono text-[11px]">
          <div className="flex gap-1.5">
            <dt className="text-text-faint">{c.guestRunLength}</dt>
            <dd className="text-text">{ad.days_active != null ? formatDays(ad.days_active) : c.runLengthUnknown}</dd>
          </div>
          {ad.text_rubric_score != null ? (
            <div className="flex gap-1.5">
              <dt className="text-text-faint">{c.guestRubric}</dt>
              <dd className="text-text">{Number(ad.text_rubric_score).toFixed(1)}</dd>
            </div>
          ) : null}
        </dl>
        {ad.permalink ? (
          <a href={ad.permalink} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-accent hover:underline">
            {c.guestOpenSource} <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        ) : null}
      </div>
    </article>
  )
}

/** Read-only board opened from a guest link. No sign-in, no actions. */
export function GuestBoardPage() {
  const { token } = useParams()
  const c = useW8Copy()
  const { lang } = useLanguage()
  const [state, setState] = useState({ status: "loading", board: null })
  useGuestPageMeta()

  useEffect(() => {
    let live = true
    boardService.getGuestBoard(token)
      .then((board) => live && setState({ status: "ready", board }))
      .catch(() => live && setState({ status: "gone", board: null }))
    return () => { live = false }
  }, [token])

  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-4 sm:px-6">
          <Link to="/" className="text-sm font-semibold text-text">Helix Intelligence</Link>
          <span className="label-mono rounded-sm border border-border px-2 py-0.5 text-text-muted">{c.guestBadge}</span>
        </div>
      </header>
      <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
        {state.status === "loading" ? <SkeletonRows rows={6} /> : null}
        {state.status === "gone" ? (
          <EmptyState icon={Link2Off} size="lg" status="unavailable" title={c.guestGone} description={c.guestGoneBody} action={null} />
        ) : null}
        {state.status === "ready" ? (
          <>
            <div className="space-y-1">
              <h1 className="text-xl font-semibold">{state.board.board}</h1>
              <p className="text-xs text-text-muted">{c.guestExpires(formatDate(state.board.expires_at, lang))}</p>
            </div>
            {state.board.items.length === 0 ? (
              <p className="text-sm text-text-muted">{c.guestEmpty}</p>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {state.board.items.map((ad) => <GuestAd key={ad.id} ad={ad} c={c} />)}
              </div>
            )}
            <p className="border-t border-border pt-4 text-[11px] text-text-faint">{c.guestFooter}</p>
          </>
        ) : null}
      </div>
    </main>
  )
}

export default GuestBoardPage
