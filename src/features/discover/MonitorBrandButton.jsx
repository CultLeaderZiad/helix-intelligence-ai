import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Radar } from "lucide-react"
import { monitorService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { Button } from "@/components/ui/Button"
import { useW92Copy } from "@/i18n/w9_2Product"
import { useW9Copy } from "@/i18n/w9Product"

/**
 * W9-2 (D2): one-click "Monitor this brand" from a result or the brand
 * header. Opening it reads a preview (0 records) with the record cost per run
 * and per month and the workspace's remaining records; creating it goes
 * through the same plan, record-cap (429) and duplicate (409) checks as any
 * monitor. Hidden when the workspace has no `monitors` feature.
 * @param {{pageId?: string|null, brandName?: string|null, size?: "xs"|"sm"}} props
 */
export function MonitorBrandButton({ pageId = null, brandName = null, size = "xs" }) {
  const w = useW92Copy()
  const w9 = useW9Copy()
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [cadence, setCadence] = useState("weekly")
  const [preview, setPreview] = useState(null)
  const [state, setState] = useState("idle") // idle | loading | ready | creating | created | error
  const [message, setMessage] = useState(null)

  useEffect(() => {
    if (!open) return undefined
    let active = true
    setState("loading")
    setMessage(null)
    monitorService.previewBrandMonitor({ page_id: pageId, brand_name: brandName, cadence })
      .then((p) => { if (active) { setPreview(p); setState("ready") } })
      .catch((err) => {
        if (!active) return
        setPreview(null)
        setState("error")
        setMessage(err?.status === 402 || err?.status === 403 ? w.monitorNeedsPlan : w.monitorFailed)
      })
    return () => { active = false }
  }, [open, cadence, pageId, brandName, w])

  if (user?.feature_flags?.monitors !== true) return null
  if (!pageId && !(brandName || "").trim()) return null

  async function create() {
    setState("creating")
    setMessage(null)
    try {
      await monitorService.createBrandMonitor({ page_id: pageId, brand_name: brandName, cadence })
      setState("created")
      setMessage(w.monitorCreated)
    } catch (err) {
      setState("ready")
      const code = err?.code ?? err?.detail?.code
      setMessage(
        code === "workspace_record_cap_reached" ? w9.recordCapError
          : err?.status === 409 ? w.monitorExists
            : err?.status === 402 || err?.status === 403 ? w.monitorNeedsPlan
              : err?.message || w.monitorFailed,
      )
    }
  }

  const blocked = preview && (!preview.fits_this_month || preview.existing_monitor_id)

  return (
    <div className="relative inline-block">
      <Button size={size} variant="outline" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex items-center gap-1">
        <Radar className="h-3.5 w-3.5" aria-hidden="true" />
        {w.monitorBrand}
      </Button>
      {open ? (
        <div role="dialog" aria-label={w.monitorBrandTitle(brandName || pageId)} className="absolute end-0 z-30 mt-1 w-72 space-y-2 rounded-lg border border-border bg-surface p-3 text-xs shadow-xl">
          <p className="font-semibold text-text" dir="auto">{w.monitorBrandTitle(brandName || pageId)}</p>
          {preview ? (
            <p className="text-text-muted" dir="auto">
              {preview.watch === "page_id" ? w.monitorWatchPage(preview.query) : w.monitorWatchName(preview.query)}
            </p>
          ) : null}
          <label className="flex items-center gap-2">
            <span>{w.monitorCadence}</span>
            <select value={cadence} onChange={(e) => setCadence(e.target.value)} className="rounded border border-border bg-surface-2 px-1 py-0.5">
              <option value="weekly">{w.cadenceWeekly}</option>
              <option value="daily">{w.cadenceDaily}</option>
            </select>
          </label>
          {state === "loading" ? <p className="text-text-faint">{w.monitorLoading}</p> : null}
          {preview ? (
            <div className="space-y-1" data-testid="monitor-brand-cost">
              <p>{w.monitorCost(preview.records_per_run, preview.records_per_month)}</p>
              <p className="text-text-faint">{w.monitorRemaining(preview.records_remaining, preview.records_cap)}</p>
              {!preview.fits_this_month ? <p className="text-warning">{w.monitorNoRoom}</p> : null}
              {preview.existing_monitor_id ? <p className="text-warning">{w.monitorExists}</p> : null}
            </div>
          ) : null}
          {message ? <p role={state === "created" ? "status" : "alert"} className={state === "created" ? "text-accent" : "text-danger"}>{message}</p> : null}
          <div className="flex items-center gap-2">
            {state === "created" || preview?.existing_monitor_id ? (
              <Button as={Link} to="/monitors" size="xs" variant="primary">{w.monitorOpen}</Button>
            ) : (
              <Button size="xs" variant="primary" disabled={!preview || blocked || state === "creating"} onClick={create}>
                {w.monitorCreate}
              </Button>
            )}
            <Button size="xs" variant="ghost" onClick={() => setOpen(false)}>{w.cancel}</Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
