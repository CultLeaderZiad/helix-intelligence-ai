import { useEffect, useState } from "react"
import { Users } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { boardService } from "@/services"
import { useW8Copy } from "@/i18n/w8Product"
import { formatDays } from "@/lib/format"

/**
 * Boards of everyone currently in this workspace. Read-only: only a board's
 * owner can add, remove or share. Rendered only when the workspace has the
 * `team_accounts` flag (the API enforces the same flag).
 */
export function TeamBoardsPanel() {
  const c = useW8Copy()
  const [boards, setBoards] = useState(null)
  const [open, setOpen] = useState(null)
  const [detail, setDetail] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let live = true
    boardService.listTeamBoards()
      .then((res) => live && setBoards((res?.items ?? []).filter((b) => !b.is_mine)))
      .catch(() => live && setFailed(true))
    return () => { live = false }
  }, [])

  async function show(board) {
    const key = `${board.owner_id}/${board.name}`
    if (open === key) { setOpen(null); setDetail(null); return }
    setOpen(key)
    setDetail(null)
    setFailed(false)
    try {
      setDetail(await boardService.getTeamBoard(board.owner_id, board.name))
    } catch {
      setFailed(true)
    }
  }

  if (boards === null && !failed) return null

  return (
    <section className="space-y-3 rounded-md border border-border bg-surface p-4" aria-label={c.teamBoardsTitle}>
      <div className="flex items-center gap-2">
        <Users className="h-4 w-4 text-accent" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-text">{c.teamBoardsTitle}</h2>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{c.teamBoardsBody}</p>
      {failed ? <p role="alert" className="text-xs text-danger">{c.shareFailed}</p> : null}
      {boards && boards.length === 0 ? <p className="text-xs text-text-faint">{c.teamBoardsNone}</p> : null}
      <ul className="divide-y divide-border border-y border-border">
        {(boards ?? []).map((board) => {
          const key = `${board.owner_id}/${board.name}`
          return (
            <li key={key} className="py-2">
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="font-semibold text-text">{board.name}</span>
                <span className="text-text-muted">{c.teamBoardsBy(board.owner_name, board.count)}</span>
                <Button size="xs" variant="outline" className="ms-auto" onClick={() => show(board)} aria-expanded={open === key}>
                  {open === key ? c.teamBoardsHide : c.teamBoardsView}
                </Button>
              </div>
              {open === key && detail ? (
                <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {detail.items.map((ad) => (
                    <li key={ad.id} className="rounded-sm border border-border bg-surface-2 p-2 text-xs">
                      <div className="label-mono text-text-faint">{ad.brand_name || "—"}</div>
                      <div className="font-semibold text-text">{ad.headline || ad.body?.slice(0, 80) || "—"}</div>
                      <div className="font-mono text-[11px] text-text-muted">
                        {c.guestRunLength}: {ad.days_active != null ? formatDays(ad.days_active) : c.runLengthUnknown}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default TeamBoardsPanel
