import React from "react"
import { FileText, Globe2, Coins, Target } from "lucide-react"

/**
 * BriefForm — stage 4.1 inputs. icp is required; geos default [SA,AE,JO,EG];
 * credit_budget gates the enqueue (402 when short).
 * Presentational only — the page owns state (Page → hook → services).
 */
export function BriefForm({ value, onChange, disabled }) {
  const set = (patch) => onChange({ ...value, ...patch })
  const field =
    "w-full rounded border border-border bg-[#09090b] px-2.5 py-1.5 font-mono text-xs text-white placeholder:text-text-faint focus:border-accent/60 focus:outline-none"
  const label = "flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-text-faint font-semibold"

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <span className={label}>
          <Target className="h-3.5 w-3.5" /> icp <span className="text-danger">*</span>
        </span>
        <textarea
          rows={2}
          disabled={disabled}
          value={value.icp}
          onChange={(e) => set({ icp: e.target.value })}
          placeholder="e.g. KSA construction main contractors"
          className={field}
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="space-y-1.5">
          <span className={label}><Globe2 className="h-3.5 w-3.5" /> geos</span>
          <input
            disabled={disabled}
            value={(value.geos || []).join(", ")}
            onChange={(e) => set({ geos: e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) })}
            placeholder="SA, AE, JO, EG"
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}>max pages</span>
          <input
            type="number" min={1} disabled={disabled}
            value={value.max_pages}
            onChange={(e) => set({ max_pages: Math.max(1, parseInt(e.target.value || "1", 10)) })}
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}>max leads</span>
          <input
            type="number" min={1} disabled={disabled}
            value={value.max_leads}
            onChange={(e) => set({ max_leads: Math.max(1, parseInt(e.target.value || "1", 10)) })}
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}><Coins className="h-3.5 w-3.5" /> credit budget</span>
          <input
            type="number" min={1} step="0.5" disabled={disabled}
            value={value.credit_budget}
            onChange={(e) => set({ credit_budget: parseFloat(e.target.value || "0") })}
            className={field}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <div className="space-y-1.5">
          <span className={label}><FileText className="h-3.5 w-3.5" /> languages</span>
          <input
            disabled={disabled}
            value={(value.languages || []).join(", ")}
            onChange={(e) => set({ languages: e.target.value.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean) })}
            placeholder="ar, en"
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}>exclude domains</span>
          <input
            disabled={disabled}
            value={(value.exclude_domains || []).join(", ")}
            onChange={(e) => set({ exclude_domains: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
            placeholder="competitor.com, spam.net"
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}>outreach min score</span>
          <input
            type="number" min={0} max={100} disabled={disabled}
            value={value.outreach_min_score}
            onChange={(e) => set({ outreach_min_score: Math.min(100, Math.max(0, parseInt(e.target.value || "0", 10))) })}
            className={field}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-4 pt-1">
        <label className="flex items-center gap-2 text-[11px] font-mono text-text-muted">
          <input type="checkbox" className="accent-accent" disabled={disabled}
            checked={value.enrich_emails}
            onChange={(e) => set({ enrich_emails: e.target.checked })} />
          enrich emails (Hunter BYOK when configured)
        </label>
        <label className="flex items-center gap-2 text-[11px] font-mono text-text-muted">
          <input type="checkbox" className="accent-accent" disabled={disabled}
            checked={value.generate_outreach}
            onChange={(e) => set({ generate_outreach: e.target.checked })} />
          draft outreach (never auto-sent)
        </label>
      </div>
    </div>
  )
}

export default BriefForm
