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
            <th className="py-2.5 px-2 font-semibold">TYPE</th>
            <th className="py-2.5 px-3 font-semibold">PRIMARY NICHE</th>
            <th className="py-2.5 px-2 font-semibold text-center">SCORE</th>
            <th className="py-2.5 px-2 font-semibold text-center">PRIORITY</th>
            <th className="py-2.5 px-3 font-semibold">EMAIL</th>
            <th className="py-2.5 px-2 font-semibold text-right">STATUS</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {leads.map((lead) => {
            const isSelected = selectedLead?.id === lead.id
            const badge = PLATFORM_BADGES[lead.platform.toLowerCase()] || {
              code: lead.platform.substring(0, 2).toUpperCase(),
              bg: "bg-surface-3 text-text-muted border-border",
            }
            const atlas = lead.atlas || {}
            const analysis = atlas.profile_analysis || {}
            const scoring = atlas.lead_scoring || {}
            const priority = (scoring.priority_level || lead.sources?.priority || "low").toLowerCase()
            const accountType = analysis.account_type || lead.sources?.account_type || "creator"
            const primaryNiche = analysis.primary_niche || lead.sources?.primary_niche || "General"
            const scrapeStatus = lead.scrape_status || "ok"

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
                {/* Handle & Platform */}
                <td className="py-3 px-3">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "inline-block rounded px-1.5 py-0.5 text-[9.5px] font-bold border shrink-0",
                        badge.bg
                      )}
                    >
                      {badge.code}
                    </span>
                    <span className={cn("font-semibold truncate max-w-[130px]", isSelected ? "text-white" : "text-text")}>
                      {lead.handle}
                    </span>
                  </div>
                </td>

                {/* Account Type */}
                <td className="py-3 px-2">
                  <span className="capitalize text-[11px] text-text-muted">
                    {accountType}
                  </span>
                </td>

                {/* Primary Niche */}
                <td className="py-3 px-3 text-text-muted truncate max-w-[140px]">
                  <span className="text-[11px] truncate block text-text">
                    {primaryNiche}
                  </span>
                </td>

                {/* Atlas Score */}
                <td className="py-3 px-2 text-center">
                  <span className="font-bold text-accent tnum text-xs">
                    {lead.lead_score}
                  </span>
                </td>

                {/* Priority Badge */}
                <td className="py-3 px-2 text-center">
                  <span
                    className={cn(
                      "inline-block rounded px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wider border",
                      priority === "high"
                        ? "bg-accent/15 text-accent border-accent/40"
                        : priority === "medium"
                        ? "bg-amber-500/15 text-amber-400 border-amber-500/40"
                        : "bg-surface-3 text-text-faint border-border"
                    )}
                  >
                    {priority}
                  </span>
                </td>

                {/* Email */}
                <td className="py-3 px-3 text-text-muted truncate max-w-[160px]">
                  {lead.email ? (
                    <span className="text-text truncate block">{lead.email}</span>
                  ) : (
                    <span className="text-text-faint text-[10px]">No email</span>
                  )}
                </td>

                {/* Scrape Status */}
                <td className="py-3 px-2 text-right">
                  <span
                    className={cn(
                      "text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border inline-block",
                      scrapeStatus === "ok" || scrapeStatus === "verified"
                        ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                        : scrapeStatus === "needs_manual_review"
                        ? "border-amber-500/30 text-amber-400 bg-amber-500/10"
                        : "border-border text-text-faint bg-surface-3"
                    )}
                  >
                    {scrapeStatus === "ok" ? "VERIFIED" : scrapeStatus === "needs_manual_review" ? "REVIEW" : scrapeStatus}
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
