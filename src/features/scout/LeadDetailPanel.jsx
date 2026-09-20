import React, { useState } from "react"
import { Copy, Check, ExternalLink, Sparkles, User, Target, Send, Code, ShieldAlert, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

export function LeadDetailPanel({ lead }) {
  const [activeTab, setActiveTab] = useState("profile") // "profile" | "score" | "outreach" | "json"
  const [copiedKey, setCopiedKey] = useState(null)

  if (!lead) {
    return (
      <div className="rounded-[4px] border border-border bg-surface p-6 font-mono text-center text-xs text-text-faint">
        Select a lead from the table to inspect Atlas intelligence
      </div>
    )
  }

  // Derive Atlas contract object
  const atlas = lead.atlas || {
    profile_analysis: {
      account_type: lead.sources?.account_type || "unknown",
      primary_niche: lead.sources?.primary_niche || "General",
      secondary_niches: [],
      influence_level: lead.followers > 100000 ? "macro" : lead.followers > 20000 ? "mid" : lead.followers > 5000 ? "micro" : "nano",
      engagement_metrics: {
        follower_count: lead.followers || 0,
        avg_engagement_rate: null,
        engagement_quality: "unknown"
      }
    },
    lead_scoring: {
      relevance_score: lead.lead_score ?? 0,
      priority_level: (lead.lead_score >= 75 ? "high" : lead.lead_score >= 50 ? "medium" : "low"),
      category_match: lead.sources?.category_match || "Category assessment",
      reasoning: lead.sources?.reasoning || "Deterministic pipeline score"
    },
    enrichment_data: {
      email: lead.email,
      email_source: lead.sources?.email_source,
      phone: lead.phone,
      website: lead.website,
      key_topics: lead.sources?.key_topics || [],
      content_sentiment: "neutral"
    },
    outreach: lead.sources?.outreach || null,
    meta: {
      platform: lead.platform,
      handle: lead.handle,
      profile_url: lead.profile_url,
      scrape_status: lead.scrape_status || "ok",
      error: null
    }
  }

  const analysis = atlas.profile_analysis || {}
  const scoring = atlas.lead_scoring || {}
  const enrichment = atlas.enrichment_data || {}
  const outreach = atlas.outreach || lead.sources?.outreach
  const meta = atlas.meta || {}

  const priority = (scoring.priority_level || "low").toLowerCase()
  const score = scoring.relevance_score ?? lead.lead_score ?? 0
  const scrapeStatus = meta.scrape_status || lead.scrape_status || "ok"

  const handleCopy = (text, key) => {
    if (!text) return
    navigator.clipboard.writeText(typeof text === "object" ? JSON.stringify(text, null, 2) : String(text))
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <div className="rounded-[4px] border border-border bg-surface font-mono overflow-hidden flex flex-col">
      {/* Header with Title & Copy Atlas JSON */}
      <div className="p-3.5 border-b border-border bg-surface-2 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-[0.14em] text-accent font-semibold">
              ATLAS LEAD
            </span>
            <span
              className={cn(
                "text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border inline-flex items-center gap-1",
                scrapeStatus === "ok" || scrapeStatus === "verified"
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : scrapeStatus === "needs_manual_review"
                  ? "border-amber-500/30 text-amber-400 bg-amber-500/10"
                  : "border-red-500/30 text-red-400 bg-red-500/10"
              )}
            >
              {scrapeStatus === "ok" ? (
                <>
                  <CheckCircle2 className="h-2.5 w-2.5" /> VERIFIED
                </>
              ) : scrapeStatus === "needs_manual_review" ? (
                <>
                  <ShieldAlert className="h-2.5 w-2.5" /> REVIEW
                </>
              ) : (
                scrapeStatus
              )}
            </span>
          </div>
          <h3 className="mt-0.5 text-sm sm:text-base font-bold text-white truncate">
            {lead.handle}
          </h3>
        </div>

        <button
          type="button"
          onClick={() => handleCopy(atlas, "atlas_json")}
          className="shrink-0 rounded border border-border bg-surface px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-text hover:border-accent hover:text-accent transition-colors flex items-center gap-1"
        >
          {copiedKey === "atlas_json" ? (
            <>
              <Check className="h-3 w-3 text-accent" /> COPIED JSON
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 text-text-faint" /> COPY JSON
            </>
          )}
        </button>
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-4 border-b border-border text-[11px] font-semibold bg-surface">
        <button
          type="button"
          onClick={() => setActiveTab("profile")}
          className={cn(
            "py-2 px-1 text-center transition-colors border-b-2 flex items-center justify-center gap-1",
            activeTab === "profile"
              ? "border-accent text-white bg-accent/5 font-bold"
              : "border-transparent text-text-muted hover:text-white"
          )}
        >
          <User className="h-3 w-3" />
          <span>Profile</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("score")}
          className={cn(
            "py-2 px-1 text-center transition-colors border-b-2 flex items-center justify-center gap-1",
            activeTab === "score"
              ? "border-accent text-white bg-accent/5 font-bold"
              : "border-transparent text-text-muted hover:text-white"
          )}
        >
          <Target className="h-3 w-3" />
          <span>Score</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("outreach")}
          className={cn(
            "py-2 px-1 text-center transition-colors border-b-2 flex items-center justify-center gap-1",
            activeTab === "outreach"
              ? "border-accent text-white bg-accent/5 font-bold"
              : "border-transparent text-text-muted hover:text-white"
          )}
        >
          <Send className="h-3 w-3" />
          <span>Outreach</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("json")}
          className={cn(
            "py-2 px-1 text-center transition-colors border-b-2 flex items-center justify-center gap-1",
            activeTab === "json"
              ? "border-accent text-white bg-accent/5 font-bold"
              : "border-transparent text-text-muted hover:text-white"
          )}
        >
          <Code className="h-3 w-3" />
          <span>JSON</span>
        </button>
      </div>

      {/* Tab Body */}
      <div className="p-4 space-y-4 text-xs">
        {/* ============================================================ */}
        {/* TAB 1: PROFILE */}
        {/* ============================================================ */}
        {activeTab === "profile" && (
          <div className="space-y-3">
            <div className="space-y-2 text-xs">
              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                <span className="text-text-faint uppercase text-[10px]">PLATFORM</span>
                <span className="text-text capitalize font-medium">{lead.platform}</span>
              </div>

              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                <span className="text-text-faint uppercase text-[10px]">ACCOUNT TYPE</span>
                <span className="text-text capitalize font-medium">
                  {analysis.account_type || "Unknown"}
                </span>
              </div>

              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                <span className="text-text-faint uppercase text-[10px]">FOLLOWERS</span>
                <span className="text-text font-medium tnum">
                  {lead.followers ? Number(lead.followers).toLocaleString() : "—"}
                </span>
              </div>

              {lead.website && (
                <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                  <span className="text-text-faint uppercase text-[10px]">WEBSITE</span>
                  <a
                    href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent hover:underline truncate max-w-[180px] inline-flex items-center gap-1"
                  >
                    {lead.website.replace(/^https?:\/\//, "")}
                    <ExternalLink className="h-3 w-3 inline shrink-0" />
                  </a>
                </div>
              )}

              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                <span className="text-text-faint uppercase text-[10px]">EMAIL</span>
                <span className="text-text truncate max-w-[200px]">
                  {lead.email ? (
                    <span className="text-white font-medium">{lead.email}</span>
                  ) : (
                    <span className="text-text-faint text-[10px]">No public email found</span>
                  )}
                </span>
              </div>

              {lead.phone && (
                <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-2">
                  <span className="text-text-faint uppercase text-[10px]">PHONE</span>
                  <span className="text-text font-medium">{lead.phone}</span>
                </div>
              )}

              {enrichment.key_topics && enrichment.key_topics.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-text-faint uppercase text-[10px] block">DETECTED TOPICS</span>
                  <div className="flex flex-wrap gap-1">
                    {enrichment.key_topics.map((t, idx) => (
                      <span
                        key={idx}
                        className="rounded bg-surface-2 border border-border px-1.5 py-0.5 text-[10px] text-text-muted"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Bio Box */}
            {lead.bio && (
              <div className="rounded-[4px] border border-border/80 bg-surface-2 p-2.5 text-[11px] text-text-muted leading-relaxed">
                <span className="text-text-faint block uppercase text-[9.5px] font-bold mb-1">
                  Scraped Bio
                </span>
                {lead.bio}
              </div>
            )}

            {/* Copy Email Button */}
            {lead.email && (
              <button
                type="button"
                onClick={() => handleCopy(lead.email, "email")}
                className="w-full rounded-[4px] py-2 font-mono text-xs font-bold uppercase tracking-wider bg-accent text-black hover:bg-[#e4ff75] transition-all flex items-center justify-center gap-2"
              >
                {copiedKey === "email" ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-black" /> COPIED EMAIL
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-black" /> COPY EMAIL ({lead.email})
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 2: SCORE & INTELLIGENCE */}
        {/* ============================================================ */}
        {activeTab === "score" && (
          <div className="space-y-4">
            {/* Score Hero */}
            <div className="rounded-[4px] border border-border bg-surface-2 p-3 text-center space-y-2">
              <div className="flex items-center justify-between text-[10px] uppercase text-text-faint font-semibold tracking-wider">
                <span>RELEVANCE SCORE</span>
                <span
                  className={cn(
                    "px-2 py-0.5 rounded border text-[9.5px] font-bold uppercase",
                    priority === "high"
                      ? "bg-accent/15 text-accent border-accent/40"
                      : priority === "medium"
                      ? "bg-amber-500/15 text-amber-400 border-amber-500/40"
                      : "bg-surface-3 text-text-faint border-border"
                  )}
                >
                  {priority} priority
                </span>
              </div>
              <div className="text-3xl font-black text-accent tnum">{score}</div>
              <div className="h-1.5 w-full rounded-full bg-[#1c1c24] overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                />
              </div>
            </div>

            {/* Assessment Breakdown */}
            <div className="space-y-2 text-xs">
              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-1.5">
                <span className="text-text-faint uppercase text-[10px]">CATEGORY MATCH</span>
                <span className="text-white font-medium truncate max-w-[180px]">
                  {scoring.category_match || "Assessed"}
                </span>
              </div>

              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-1.5">
                <span className="text-text-faint uppercase text-[10px]">INFLUENCE TIER</span>
                <span className="text-text capitalize font-medium">
                  {analysis.influence_level || "Unknown"}
                </span>
              </div>

              <div className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-1.5">
                <span className="text-text-faint uppercase text-[10px]">ENGAGEMENT QUALITY</span>
                <span className="text-text capitalize font-medium">
                  {analysis.engagement_metrics?.engagement_quality || "Unknown"}
                </span>
              </div>
            </div>

            {/* Reasoning Box */}
            {scoring.reasoning && (
              <div className="rounded-[4px] border border-border/80 bg-surface-2 p-3 space-y-1">
                <span className="text-[10px] uppercase font-bold text-accent block">
                  Atlas Reasoning
                </span>
                <p className="text-[11.5px] text-text-muted leading-relaxed">
                  {scoring.reasoning}
                </p>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 3: OUTREACH */}
        {/* ============================================================ */}
        {activeTab === "outreach" && (
          <div className="space-y-4">
            {outreach && (outreach.email_body || outreach.dm_body) ? (
              <>
                {/* Subject Line */}
                {outreach.email_subject && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] uppercase text-text-faint font-semibold">
                      <span>EMAIL SUBJECT</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(outreach.email_subject, "subj")}
                        className="text-accent hover:underline flex items-center gap-1"
                      >
                        {copiedKey === "subj" ? <Check className="h-2.5 w-2.5" /> : <Copy className="h-2.5 w-2.5" />}
                        {copiedKey === "subj" ? "COPIED" : "COPY"}
                      </button>
                    </div>
                    <div className="rounded-[4px] border border-border bg-surface-2 p-2 text-[11.5px] text-white font-medium">
                      {outreach.email_subject}
                    </div>
                  </div>
                )}

                {/* Cold Email Body */}
                {outreach.email_body && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] uppercase text-text-faint font-semibold">
                      <span>COLD EMAIL DRAFT</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(outreach.email_body, "email_body")}
                        className="text-accent hover:underline flex items-center gap-1"
                      >
                        {copiedKey === "email_body" ? <Check className="h-2.5 w-2.5" /> : <Copy className="h-2.5 w-2.5" />}
                        {copiedKey === "email_body" ? "COPIED" : "COPY EMAIL"}
                      </button>
                    </div>
                    <div className="rounded-[4px] border border-border bg-surface-2 p-2.5 text-[11px] text-text-muted leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                      {outreach.email_body}
                    </div>
                  </div>
                )}

                {/* Social DM */}
                {outreach.dm_body && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] uppercase text-text-faint font-semibold">
                      <span>INSTAGRAM / SOCIAL DM</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(outreach.dm_body, "dm_body")}
                        className="text-accent hover:underline flex items-center gap-1"
                      >
                        {copiedKey === "dm_body" ? <Check className="h-2.5 w-2.5" /> : <Copy className="h-2.5 w-2.5" />}
                        {copiedKey === "dm_body" ? "COPIED" : "COPY DM"}
                      </button>
                    </div>
                    <div className="rounded-[4px] border border-border bg-surface-2 p-2.5 text-[11px] text-text-muted leading-relaxed whitespace-pre-wrap">
                      {outreach.dm_body}
                    </div>
                  </div>
                )}

                {/* Personalization Points */}
                {outreach.personalization_points && outreach.personalization_points.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-text-faint uppercase text-[10px] block font-semibold">
                      PERSONALIZATION HOOKS
                    </span>
                    <ul className="space-y-1 text-[11px] text-text-muted">
                      {outreach.personalization_points.map((pt, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <Sparkles className="h-3 w-3 text-accent shrink-0 mt-0.5" />
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-[4px] border border-border bg-surface-2 p-5 text-center space-y-2">
                <div className="text-accent font-bold text-xs uppercase tracking-wider">
                  Outreach Skipped / Low Priority
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed max-w-xs mx-auto">
                  Outreach drafts are generated automatically for profiles classified with medium or high priority (score &ge; 50). This profile scored {score}/100.
                </p>
                {lead.email && (
                  <button
                    type="button"
                    onClick={() => handleCopy(lead.email, "email_outreach_fallback")}
                    className="mt-2 rounded bg-surface border border-border px-3 py-1 text-[11px] text-white hover:border-accent hover:text-accent font-semibold"
                  >
                    Copy Direct Email ({lead.email})
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 4: RAW ATLAS JSON */}
        {/* ============================================================ */}
        {activeTab === "json" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px] text-text-faint uppercase">
              <span>Atlas Contract Schema</span>
              <button
                type="button"
                onClick={() => handleCopy(atlas, "raw_json")}
                className="text-accent hover:underline flex items-center gap-1"
              >
                {copiedKey === "raw_json" ? <Check className="h-2.5 w-2.5" /> : <Copy className="h-2.5 w-2.5" />}
                {copiedKey === "raw_json" ? "COPIED" : "COPY RAW JSON"}
              </button>
            </div>
            <pre className="rounded-[4px] border border-border bg-surface-2 p-3 text-[10px] text-text-muted overflow-x-auto max-h-80 leading-relaxed">
              {JSON.stringify(atlas, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
