import React, { useState } from "react"
import { Building2, Contact, Gauge, Send, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * LeadDetail - Company | Contacts | Score | Outreach | Markdown.
 * Empty stays empty; "skipped_..." reasons are shown verbatim.
 */
const TABS = [
  { id: "company", label: "Company", icon: Building2 },
  { id: "contacts", label: "Contacts", icon: Contact },
  { id: "score", label: "Score", icon: Gauge },
  { id: "outreach", label: "Outreach", icon: Send },
  { id: "markdown", label: "Markdown", icon: FileText },
]

function Row({ k, children }) {
  return (
    <div className="flex items-start gap-2 py-1 border-b border-border/50 last:border-0">
      <span className="w-32 shrink-0 text-[10px] uppercase tracking-wider text-text-faint pt-0.5">{k}</span>
      <span className="text-[11px] text-text break-all">{children ?? <span className="text-text-faint">-</span>}</span>
    </div>
  )
}

export function LeadDetail({ lead }) {
  const [tab, setTab] = useState("company")
  if (!lead) {
    return (
      <div className="rounded-[4px] border border-border bg-surface/40 p-6 text-center font-mono text-[11px] text-text-muted">
        Select a lead to inspect its provenance, score breakdown, outreach draft, and markdown artifact.
      </div>
    )
  }

  const score = lead.sources?.score || {}
  const outreach = lead.outreach || null
  const skipped = outreach?.reason

  return (
    <div className="rounded-[4px] border border-border bg-surface/60 font-mono">
      <div className="flex flex-wrap gap-1 border-b border-border p-1.5">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "flex items-center gap-1.5 rounded px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition-all",
              tab === id ? "bg-accent text-black" : "text-text-muted hover:text-white"
            )}
          >
            <Icon className="h-3 w-3" />
            {label}
          </button>
        ))}
      </div>

      <div className="p-3">
        {tab === "company" && (
          <div>
            <Row k="company">{lead.company_name}</Row>
            <Row k="website">
              {lead.website ? (
                <a href={lead.website} target="_blank" rel="noreferrer noopener" className="text-accent hover:underline">
                  {lead.website}
                </a>
              ) : null}
            </Row>
            <Row k="domain">{lead.domain}</Row>
            <Row k="address">{lead.address}</Row>
            <Row k="socials">
              {Object.keys(lead.socials || {}).length > 0
                ? Object.entries(lead.socials).map(([k, v]) => (
                    <a key={k} href={v} target="_blank" rel="noreferrer noopener" className="mr-2 text-accent hover:underline">
                      {k}
                    </a>
                  ))
                : null}
            </Row>
            <Row k="fetch status">{lead.fetch_status}</Row>
            <Row k="extract status">{lead.extract_status}</Row>
            <Row k="engine used">{lead.engine_used}</Row>
            <Row k="pages visited">{(lead.sources?.urls || []).length}</Row>
          </div>
        )}

        {tab === "contacts" && (
          <div className="space-y-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-text-faint">emails</span>
                <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase text-white">
                  source: {lead.email_source || "none"}
                </span>
              </div>
              {(lead.emails || []).length > 0 ? (
                <ul className="mt-1 space-y-0.5">
                  {lead.emails.map((e) => (
                    <li key={e} className="text-[11px] text-text">{e}</li>
                  ))}
                </ul>
              ) : (
                <div className="mt-1 text-[11px] text-text-faint">none found - left empty, not invented</div>
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-text-faint">phones</span>
                <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase text-white">
                  source: {lead.phone_source || "none"}
                </span>
              </div>
              {(lead.phones || []).length > 0 ? (
                <ul className="mt-1 space-y-0.5">
                  {lead.phones.map((p) => (
                    <li key={p} className="text-[11px] text-text">{p}</li>
                  ))}
                </ul>
              ) : (
                <div className="mt-1 text-[11px] text-text-faint">none found - left empty, not invented</div>
              )}
            </div>
            {lead.sources?.hunter_confidence && (
              <div className="text-[10px] text-text-faint">
                hunter confidence: {(lead.sources.hunter_confidence || []).join(", ")}
              </div>
            )}
          </div>
        )}

        {tab === "score" && (
          <div>
            <div className="flex items-baseline gap-2">
              <span className="tnum text-3xl font-bold text-white">{lead.lead_score ?? 0}</span>
              <span className="text-[11px] uppercase tracking-wider text-text-muted">{lead.priority || "unscored"}</span>
            </div>
            <div className="mt-2">
              <Row k="formula">{score.formula || "-"}</Row>
              <Row k="icp keyword hits">{score.icp_keyword_overlaps ?? 0}</Row>
              <Row k="bands">{score.priority_bands ? `high ${score.priority_bands.high} . med ${score.priority_bands.med} . low ${score.priority_bands.low}` : "-"}</Row>
              <Row k="contact signal">{lead.sources?.contact_signal ? "yes" : "no"}</Row>
              <Row k="selector hits">
                {lead.sources?.selector_hits ? JSON.stringify(lead.sources.selector_hits) : "-"}
              </Row>
            </div>
          </div>
        )}

        {tab === "outreach" && (
          <div className="space-y-2">
            {outreach?.subject && outreach?.body ? (
              <>
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-text-faint">subject</span>
                  <div className="text-[11px] text-white">{outreach.subject}</div>
                </div>
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-text-faint">body</span>
                  <div className="whitespace-pre-wrap text-[11px] text-text">{outreach.body}</div>
                </div>
                {outreach.dm && (
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-faint">social dm</span>
                    <div className="whitespace-pre-wrap text-[11px] text-text">{outreach.dm}</div>
                  </div>
                )}
                {(outreach.personalization_points || []).length > 0 && (
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-faint">personalization</span>
                    <ul className="mt-0.5 list-disc pl-4">
                      {outreach.personalization_points.map((p, i) => (
                        <li key={i} className="text-[11px] text-text-muted">{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="text-[10px] text-warning">draft only - Helix never sends outreach</div>
              </>
            ) : (
              <div className="text-[11px] text-text-muted">
                {skipped ? `skipped - ${skipped}` : "no outreach draft on this lead"}
                {outreach?.detail ? ` (${outreach.detail})` : ""}
              </div>
            )}
          </div>
        )}

        {tab === "markdown" && (
          <div className="space-y-2">
            <Row k="artifact">{lead.markdown_artifact_path}</Row>
            {lead.markdown_excerpt ? (
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded border border-border bg-[#09090b] p-2 text-[11px] text-text-muted">
                {lead.markdown_excerpt}
              </pre>
            ) : (
              <div className="text-[11px] text-text-faint">no markdown captured for this page</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default LeadDetail
