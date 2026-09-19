import React from "react"
import { cn } from "@/lib/utils"

const PLATFORM_BADGES = {
  instagram: { code: "IG", bg: "bg-pink-500/10 text-pink-400 border-pink-500/30" },
  github: { code: "GH", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  linktree: { code: "LT", bg: "bg-lime-500/10 text-lime-400 border-lime-500/30" },
  tiktok: { code: "TT", bg: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" },
  linkedin: { code: "LI", bg: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
  youtube: { code: "YT", bg: "bg-red-500/10 text-red-400 border-red-500/30" },
  twitch: { code: "TW", bg: "bg-purple-500/10 text-purple-400 border-purple-500/30" },
  pinterest: { code: "PI", bg: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
}

export function LeadsTable({ leads, selectedLead, onSelectLead }) {
  return (
    <div className="w-full overflow-x-auto rounded-[4px] border border-border bg-surface">
      <table className="w-full text-left font-mono text-xs border-collapse">
        <thead>
          <tr className="border-b border-border bg-surface-2 text-[10px] uppercase tracking-[0.1em] text-text-faint sticky top-0 z-10">
            <th className="py-2.5 px-3 font-semibold">HANDLE</th>
            <th className="py-2.5 px-2 font-semibold">PLATFORM</th>
            <th className="py-2.5 px-3 font-semibold">NAME</th>
            <th className="py-2.5 px-3 font-semibold">EMAIL</th>
            <th className="py-2.5 px-3 font-semibold">PHONE</th>
            <th className="py-2.5 px-3 font-semibold text-right">SCORE</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {leads.map((lead) => {
            const isSelected = selectedLead?.id === lead.id
            const badge = PLATFORM_BADGES[lead.platform.toLowerCase()] || {
              code: lead.platform.substring(0, 2).toUpperCase(),
              bg: "bg-surface-3 text-text-muted border-border",
            }

            return (
              <tr
                key={lead.id}
                onClick={() => onSelectLead(lead)}
                className={cn(
                  "cursor-pointer transition-colors group select-none",
                  isSelected
                    ? "bg-surface-2 text-text font-medium"
                    : "hover:bg-surface-2/60 text-text-muted"
                )}
              >
                <td className="py-3 px-3">
                  <span className={cn("font-semibold", isSelected ? "text-white" : "text-text")}>
                    {lead.handle}
                  </span>
                </td>
                <td className="py-3 px-2">
                  <span
                    className={cn(
                      "inline-block rounded px-1.5 py-0.5 text-[9.5px] font-bold border",
                      badge.bg
                    )}
                  >
                    {badge.code}
                  </span>
                </td>
                <td className="py-3 px-3 text-text-muted truncate max-w-[140px]">
                  {lead.name || "—"}
                </td>
                <td className="py-3 px-3 text-text-muted truncate max-w-[160px]">
                  {lead.email ? (
                    <span className="text-text">{lead.email}</span>
                  ) : (
                    <span className="text-text-faint">—</span>
                  )}
                </td>
                <td className="py-3 px-3 text-text-muted truncate max-w-[110px]">
                  {lead.phone ? (
                    <span className="text-text">{lead.phone}</span>
                  ) : (
                    <span className="text-text-faint">—</span>
                  )}
                </td>
                <td className="py-3 px-3 text-right">
                  <span className="font-bold text-accent tnum">
                    {lead.lead_score}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
