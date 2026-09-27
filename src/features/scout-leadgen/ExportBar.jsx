import React, { useState } from "react"
import { Download, FileText, FileJson } from "lucide-react"

/**
 * ExportBar — CSV + JSONL downloads with provenance columns
 * (email_source, phone_source, extract_status, fetch_status, engine, sources).
 * Headers-only when a job has zero leads — never fabricated rows.
 */
export function ExportBar({ job, leadsCount, onExportCsv, onExportJsonl }) {
  const [busy, setBusy] = useState(null)
  const ready = job && (job.status === "succeeded" || job.status === "failed" || (leadsCount || 0) > 0)

  const run = async (kind, fn) => {
    setBusy(kind)
    try {
      await fn()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
      <span className="flex items-center gap-1.5 uppercase tracking-wider text-text-faint">
        <Download className="h-3.5 w-3.5" /> export
      </span>
      <button
        type="button"
        disabled={!ready || busy}
        onClick={() => run("csv", onExportCsv)}
        className="flex items-center gap-1.5 rounded border border-border bg-surface px-2.5 py-1 font-semibold uppercase tracking-wider text-white hover:border-accent/50 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <FileText className="h-3.5 w-3.5" />
        {busy === "csv" ? "exporting…" : "CSV"}
      </button>
      <button
        type="button"
        disabled={!ready || busy}
        onClick={() => run("jsonl", onExportJsonl)}
        className="flex items-center gap-1.5 rounded border border-border bg-surface px-2.5 py-1 font-semibold uppercase tracking-wider text-white hover:border-accent/50 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <FileJson className="h-3.5 w-3.5" />
        {busy === "jsonl" ? "exporting…" : "JSONL"}
      </button>
      {ready && (
        <span className="text-text-muted tnum">
          {leadsCount || 0} row{(leadsCount || 0) === 1 ? "" : "s"} · provenance columns included
        </span>
      )}
    </div>
  )
}

export default ExportBar
