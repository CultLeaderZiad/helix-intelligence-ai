import React from "react"
import { Crosshair, AlertTriangle, Inbox } from "lucide-react"

/**
 * Honest empty states — worker offline / no jobs / no leads.
 * Never imply fake live success (no Sample/demo CTAs on Lead Generation).
 */

export function WorkerOfflineState({ onRefresh }) {
  return (
    <div className="rounded-[4px] border border-danger/40 bg-danger/5 p-8 text-center font-mono space-y-3">
      <div className="mx-auto w-10 h-10 rounded-[4px] border border-danger/50 bg-danger/10 flex items-center justify-center text-danger">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h4 className="text-sm font-semibold text-white">Worker offline</h4>
      <p className="text-xs text-text-muted max-w-md mx-auto">
        The Scrapling worker is not reporting in, so no Lead Generation jobs can be queued.
        Start the worker (SCRAPLING_WORKER_ENABLED=true) — no leads are shown until real jobs run.
      </p>
      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          className="rounded px-3 py-1.5 border border-border bg-surface text-xs font-semibold uppercase tracking-wider text-white hover:border-accent/50"
        >
          Re-check health
        </button>
      )}
    </div>
  )
}

export function NoLeadsState({ job }) {
  const failed = job?.status === "failed"
  return (
    <div className="rounded-[4px] border border-border bg-surface/40 p-8 text-center font-mono space-y-2">
      <div className="mx-auto w-10 h-10 rounded-[4px] border border-border bg-surface flex items-center justify-center text-text-muted">
        <Inbox className="h-5 w-5" />
      </div>
      <div className="text-white text-xs font-semibold">
        {failed ? "Job failed before any leads were found" : "No leads extracted yet"}
      </div>
      <div className="text-text-muted text-[11px] max-w-md mx-auto">
        {failed
          ? job?.error_msg || "Check the job transcript above for the honest failure reason."
          : "Leads appear here only when the worker extracts real public contact fields. Empty fields stay empty — nothing is fabricated."}
      </div>
    </div>
  )
}

export function IdleState({ onRunHint }) {
  return (
    <div className="rounded-[4px] border border-border bg-surface/50 p-10 text-center font-mono space-y-3">
      <div className="mx-auto w-10 h-10 rounded-[4px] border border-accent/40 bg-accent/10 flex items-center justify-center text-accent">
        <Crosshair className="h-5 w-5" />
      </div>
      <h4 className="text-sm font-semibold text-white">Lead Generation</h4>
      <p className="text-xs text-text-muted max-w-md mx-auto">
        Write an ICP brief, seed public URLs (or a sitemap / Shopify store / domain list), and let the
        Scrapling worker discover, extract, and score real public contact fields — with provenance on
        every email and phone. Robots.txt honored by default. Outreach is drafted, never sent.
      </p>
      {onRunHint && <div className="text-[11px] text-text-faint">{onRunHint}</div>}
    </div>
  )
}
