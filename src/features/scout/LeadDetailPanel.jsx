import React, { useState } from "react"
import { Copy, Check, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

export function LeadDetailPanel({ lead }) {
  const [copied, setCopied] = useState(false)

  if (!lead) {
    return (
      <div className="rounded-[4px] border border-border bg-surface p-6 font-mono text-center text-xs text-text-faint">
        Select a lead from the table to inspect details
      </div>
    )
  }

  const handleCopyEmail = () => {
    if (!lead.email) return
    navigator.clipboard.writeText(lead.email)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const emailSource = lead.sources?.email_source ? ` · ${lead.sources.email_source}` : ""
  const emailConf = lead.sources?.confidence ? ` · ${lead.sources.confidence}` : ""
  const phoneSource = lead.sources?.phone_source ? ` · ${lead.sources.phone_source}` : ""

  return (
    <div className="rounded-[4px] border border-border bg-surface p-4 sm:p-5 font-mono space-y-4">
      <div>
        <span className="block text-[10px] uppercase tracking-[0.14em] text-text-faint font-semibold">
          LEAD DETAIL
        </span>
        <h3 className="mt-1 text-base sm:text-lg font-bold text-white truncate">
          {lead.handle}
        </h3>
      </div>

      {/* KV Grid */}
      <div className="space-y-2.5 text-xs">
        <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
          <span className="text-text-faint uppercase text-[10px]">PLATFORM</span>
          <span className="text-text capitalize font-medium">{lead.platform}</span>
        </div>

        {lead.website && (
          <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
            <span className="text-text-faint uppercase text-[10px]">Website</span>
            <a
              href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
              target="_blank"
              rel="noreferrer"
              className="text-text hover:text-accent underline truncate max-w-[180px] inline-flex items-center gap-1"
            >
              {lead.website.replace(/^https?:\/\//, "")}
              <ExternalLink className="h-3 w-3 inline" />
            </a>
          </div>
        )}

        <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
          <span className="text-text-faint uppercase text-[10px]">Email</span>
          <span className="text-text truncate max-w-[200px]">
            {lead.email ? (
              <>
                {lead.email}
                <span className="text-text-faint text-[10.5px]">
                  {emailSource}
                  {emailConf}
                </span>
              </>
            ) : (
              <span className="text-text-faint">—</span>
            )}
          </span>
        </div>

        <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
          <span className="text-text-faint uppercase text-[10px]">Phone</span>
          <span className="text-text truncate max-w-[180px]">
            {lead.phone ? (
              <>
                {lead.phone}
                <span className="text-text-faint text-[10.5px]">{phoneSource}</span>
              </>
            ) : (
              <span className="text-text-faint">—</span>
            )}
          </span>
        </div>

        <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
          <span className="text-text-faint uppercase text-[10px]">Followers</span>
          <span className="text-text font-medium tnum">
            {lead.followers ? Number(lead.followers).toLocaleString() : "—"}
          </span>
        </div>

        <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
          <span className="text-text-faint uppercase text-[10px]">Lead score</span>
          <span className="text-accent font-bold tnum">
            {lead.lead_score} / 100
          </span>
        </div>
      </div>

      {/* Score bar */}
      <div className="space-y-1.5 pt-1">
        <span className="block text-[10px] uppercase tracking-[0.14em] text-text-faint font-semibold">
          SCORE
        </span>
        <div className="h-1.5 w-full rounded-full bg-[#1c1c24] overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, lead.lead_score))}%` }}
          />
        </div>
      </div>

      {/* Bio Box */}
      {lead.bio && (
        <div className="rounded-[4px] border border-border/80 bg-surface-2 p-2.5 text-[11.5px] text-text-muted leading-relaxed">
          <span className="text-text-faint">Bio: </span>
          {lead.bio}
        </div>
      )}

      {/* Copy Email Button */}
      <button
        type="button"
        disabled={!lead.email}
        onClick={handleCopyEmail}
        className={cn(
          "w-full rounded-[4px] py-2 font-mono text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2",
          lead.email
            ? "bg-accent text-black hover:bg-[#e4ff75] shadow-sm shadow-accent/20"
            : "bg-surface-2 text-text-faint border border-border cursor-not-allowed"
        )}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5 text-black" />
            COPIED TO CLIPBOARD
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5 text-black" />
            COPY EMAIL
          </>
        )}
      </button>
    </div>
  )
}
