import { useCallback, useEffect, useState } from "react"
import { Link2 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Label, Select } from "@/components/ui/Field"
import { boardService } from "@/services"
import { useW8Copy } from "@/i18n/w8Product"
import { useLanguage } from "@/context/LanguageContext"

const EXPIRY_DAYS = [1, 7, 30]

function formatDate(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang === "ar" ? "ar" : "en", { year: "numeric", month: "short", day: "numeric" })
  } catch {
    return iso
  }
}

/**
 * Create, copy and revoke guest links for one board. A guest link opens a
 * read-only view without sign-in; it expires on its own and can be revoked.
 */
export function BoardSharePanel() {
  const c = useW8Copy()
  const { lang } = useLanguage()
  const [boards, setBoards] = useState([])
  const [board, setBoard] = useState("")
  const [days, setDays] = useState(7)
  const [links, setLinks] = useState([])
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [copied, setCopied] = useState(null)

  useEffect(() => {
    let live = true
    boardService.listBoards().then((res) => {
      if (!live) return
      const items = res?.items ?? []
      setBoards(items)
      setBoard((current) => current || items[0]?.name || "")
    }).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [])

  const loadLinks = useCallback(async (name) => {
    if (!name) return setLinks([])
    try {
      const res = await boardService.listShareLinks(name)
      setLinks(res?.items ?? [])
    } catch {
      setFailed(true)
    }
  }, [])

  useEffect(() => { void loadLinks(board) }, [board, loadLinks])

  async function create() {
    setBusy(true)
    setFailed(false)
    try {
      await boardService.createShareLink({ collection: board, expires_in_days: days })
      await loadLinks(board)
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  async function revoke(id) {
    setFailed(false)
    try {
      await boardService.revokeShareLink(id)
      await loadLinks(board)
    } catch {
      setFailed(true)
    }
  }

  async function copy(link) {
    const url = `${window.location.origin}${link.url}`
    try {
      await navigator.clipboard.writeText(url)
      setCopied(link.id)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      window.prompt(c.shareCopy, url)
    }
  }

  if (boards.length === 0) return null
  const stateLabel = { active: c.shareActive, expired: c.shareExpired, revoked: c.shareRevoked }

  return (
    <section className="space-y-3 rounded-md border border-border bg-surface p-4" aria-label={c.shareTitle}>
      <div className="flex items-center gap-2">
        <Link2 className="h-4 w-4 text-accent" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-text">{c.shareTitle}</h2>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{c.shareBody}</p>
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-[160px] flex-col gap-1.5">
          <Label htmlFor="share-board">{c.shareBoard}</Label>
          <Select
            id="share-board"
            value={board}
            onChange={(e) => setBoard(e.target.value)}
            options={boards.map((b) => ({ value: b.name, label: `${b.name} (${b.count})` }))}
          />
        </div>
        <div className="flex min-w-[120px] flex-col gap-1.5">
          <Label htmlFor="share-days">{c.shareExpiry}</Label>
          <Select
            id="share-days"
            value={String(days)}
            onChange={(e) => setDays(Number(e.target.value))}
            options={EXPIRY_DAYS.map((n) => ({ value: String(n), label: c.shareDays(n) }))}
          />
        </div>
        <Button size="sm" variant="primary" onClick={create} disabled={busy || !board}>
          {busy ? c.shareCreating : c.shareCreate}
        </Button>
      </div>
      {failed ? <p role="alert" className="text-xs text-danger">{c.shareFailed}</p> : null}
      {links.length === 0 ? (
        <p className="text-xs text-text-faint">{c.shareNone}</p>
      ) : (
        <ul className="divide-y divide-border border-y border-border">
          {links.map((link) => (
            <li key={link.id} className="flex flex-wrap items-center gap-3 py-2 text-xs">
              <span className={link.state === "active" ? "label-mono text-success" : "label-mono text-text-faint"}>
                {stateLabel[link.state] ?? link.state}
              </span>
              <span className="text-text-muted">{c.shareExpires(formatDate(link.expires_at, lang))}</span>
              {link.state === "active" ? (
                <span className="ms-auto flex gap-2">
                  <Button size="xs" variant="outline" onClick={() => copy(link)}>
                    {copied === link.id ? c.shareCopied : c.shareCopy}
                  </Button>
                  <Button size="xs" variant="ghost" onClick={() => revoke(link.id)}>{c.shareRevoke}</Button>
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default BoardSharePanel
