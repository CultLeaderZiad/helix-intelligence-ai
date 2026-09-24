import React from "react"
import { Mail, Phone, ShieldQuestion } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * LeadsTable — real rows only. Contact badges show provenance
 * (website | hunter | none); empty stays visibly empty, never invented.
 */
function SourceBadge({ source }) {
  const map = {
    website: "border-success/40 text-success",
    hunter: "border-accent/40 text-accent",
    bio: "border-border text-text-muted",
    none: "border-border text-text-faint",
  }
  return (
    <span className={cn("rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase", map[source] || map.none)}>
      {source || "none"}
    </span>
  )
}

function StatusBadge({ label, value, bad }) {
  return (
    <span className={cn("rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase",
      bad ? "border-danger/40 text-danger" : "border-border text-text-muted")}>
      {label}:{value}
    </span>
  )
}

export function LeadsTable({ leads, selectedLead, onSelectLead }) {
  if (!leads || leads.length === 0) return null
  return (
    <div className="overflow-x-auto rounded-[4px] border border-border bg-surface/60">
      <table className="w-full text-left font-mono text-[11px]">
        <thead className="bg-[#0d0d11] text-text-faint uppercase tracking-wider">
          <tr>
            <th className="px-3 py-2 font-semibold">company</th>
            <th className="px-3 py-2 font-semibold">domain</th>
            <th className="px-3 py-2 font-semibold">contacts</th>
            <th className="px-3 py-2 font-semibold">score</th>
            <th className="px-3 py-2 font-semibold">status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => {
            const active = selectedLead?.id === lead.id
            return (
              <tr
                key={lead.id}
                onClick={() => onSelectLead?.(lead)}
                className={cn(
                  "cursor-pointer border-t border-border/70 transition-colors",
                  active ? "bg-accent/10" : "hover:bg-surface"
                )}
              >
                <td className="px-3 py-2">
                  <div className={cn("font-semibold", active ? "text-accent" : "text-white")}>
                    {lead.company_name || <span className="text-text-faint">— not found</span>}
                  </div>
                  {lead.address && <div className="text-text-faint truncate max-w-[240px]">{lead.address}</div>}
                </td>
                <td className="px-3 py-2 text-text-muted truncate max-w-[180px]">{lead.domain || "—"}</td>
                <td className="px-3 py-2">
                  <div className="flex flex-col gap-1">
                    <span className="flex items-center gap-1.5">
                      <Mail className="h-3 w-3 text-text-faint" />
                      <span className="tnum text-white">{(lead.emails || []).length}</span>
                      <SourceBadge source={lead.email_source} />
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Phone className="h-3 w-3 text-text-faint" />
                      <span className="tnum text-white">{(lead.phones || []).length}</span>
                      <SourceBadge source={lead.phone_source} />
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <span className="tnum text-base font-bold text-white">{lead.lead_score ?? 0}</span>
                  {lead.priority && (
                    <div className={cn("text-[10px] uppercase",
                      lead.priority === "high" ? "text-success" : lead.priority === "med" ? "text-warning" : "text-text-faint")}>
                      {lead.priority}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    <StatusBadge label="fetch" value={lead.fetch_status} bad={lead.fetch_status !== "ok"} />
                    <StatusBadge label="extract" value={lead.extract_status} bad={lead.extract_status === "failed" || lead.extract_status === "empty"} />
                    {lead.engine_used && <StatusBadge label="engine" value={lead.engine_used} />}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="flex items-center gap-2 border-t border-border/70 px-3 py-1.5 text-[10px] text-text-faint">
        <ShieldQuestion className="h-3 w-3" />
        every email/phone carries provenance · empty fields stay empty
      </div>
    </div>
  )
}

export default LeadsTable
