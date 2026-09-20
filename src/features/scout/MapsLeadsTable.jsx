import React from "react"
import { ExternalLink, Mail, Phone, MapPin, Star, Share2, Check, Copy } from "lucide-react"
import { cn } from "@/lib/utils"

export function MapsLeadsTable({ leads = [], selectedLead, onSelectLead }) {
  const [copiedId, setCopiedId] = React.useState(null)

  const handleCopy = (e, text, id) => {
    e.stopPropagation()
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  if (!leads || leads.length === 0) {
    return null
  }

  return (
    <div className="rounded-[4px] border border-border bg-surface overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between border-b border-border bg-[#141419] px-4 py-2 text-[11px] text-text-muted font-semibold uppercase tracking-wider">
        <span>Google Maps Leads ({leads.length})</span>
        <span className="text-[10px] text-accent">Click row to inspect</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border/60 bg-[#0d0d12] text-[10px] font-semibold text-text-muted uppercase tracking-wider">
              <th className="py-2.5 px-3">Business</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3">Phone</th>
              <th className="py-2.5 px-3">Email</th>
              <th className="py-2.5 px-3">Website</th>
              <th className="py-2.5 px-3">Address</th>
              <th className="py-2.5 px-3">Rating</th>
              <th className="py-2.5 px-3">Socials</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {leads.map((lead) => {
              const isSelected = selectedLead?.id === lead.id
              const hasSocials = Boolean(lead.instagram || lead.facebook || lead.linkedin || lead.twitter || (lead.socials && Object.keys(lead.socials).length > 0))

              return (
                <tr
                  key={lead.id || lead.title}
                  onClick={() => onSelectLead?.(lead)}
                  className={cn(
                    "cursor-pointer transition-colors text-[11px]",
                    isSelected
                      ? "bg-accent/10 border-l-2 border-l-accent"
                      : "hover:bg-[#181820]"
                  )}
                >
                  {/* Business Name */}
                  <td className="py-2.5 px-3 font-semibold text-white max-w-[200px] truncate">
                    {lead.title}
                  </td>

                  {/* Category */}
                  <td className="py-2.5 px-3 text-text-muted text-[10px] max-w-[140px] truncate">
                    <span className="rounded bg-[#1a1a24] px-1.5 py-0.5 border border-border/50 text-text">
                      {lead.category || "Business"}
                    </span>
                  </td>

                  {/* Phone */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    {lead.phone ? (
                      <button
                        type="button"
                        onClick={(e) => handleCopy(e, lead.phone, `phone_${lead.id}`)}
                        className="flex items-center gap-1 text-accent hover:underline"
                        title="Copy phone"
                      >
                        <Phone className="h-2.5 w-2.5" />
                        <span>{lead.phone}</span>
                        {copiedId === `phone_${lead.id}` && <Check className="h-2.5 w-2.5 text-accent ml-0.5" />}
                      </button>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </td>

                  {/* Email */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    {lead.email ? (
                      <button
                        type="button"
                        onClick={(e) => handleCopy(e, lead.email, `email_${lead.id}`)}
                        className="flex items-center gap-1 text-accent hover:underline font-semibold"
                        title="Copy email"
                      >
                        <Mail className="h-2.5 w-2.5" />
                        <span>{lead.email}</span>
                        {copiedId === `email_${lead.id}` && <Check className="h-2.5 w-2.5 text-accent ml-0.5" />}
                      </button>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </td>

                  {/* Website */}
                  <td className="py-2.5 px-3 max-w-[130px] truncate">
                    {lead.website ? (
                      <a
                        href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 text-text-muted hover:text-white truncate"
                      >
                        <span className="truncate">{lead.website.replace(/^https?:\/\//, "")}</span>
                        <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                      </a>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </td>

                  {/* Address */}
                  <td className="py-2.5 px-3 text-text-muted text-[10px] max-w-[160px] truncate" title={lead.address}>
                    {lead.address ? (
                      <span className="flex items-center gap-1 truncate">
                        <MapPin className="h-2.5 w-2.5 shrink-0 text-text-faint" />
                        <span className="truncate">{lead.address}</span>
                      </span>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </td>

                  {/* Rating */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    {lead.rating ? (
                      <div className="flex items-center gap-1 text-[10px]">
                        <Star className="h-2.5 w-2.5 text-amber-400 fill-amber-400" />
                        <span className="font-bold text-white">{lead.rating.toFixed(1)}</span>
                        {lead.reviews_count ? (
                          <span className="text-text-faint">({lead.reviews_count})</span>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </td>

                  {/* Socials */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    {hasSocials ? (
                      <div className="flex items-center gap-1.5">
                        {lead.instagram && (
                          <a
                            href={lead.instagram}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-pink-400 hover:text-pink-300 text-[10px] font-bold"
                            title="Instagram"
                          >
                            IG
                          </a>
                        )}
                        {lead.facebook && (
                          <a
                            href={lead.facebook}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-400 hover:text-blue-300 text-[10px] font-bold"
                            title="Facebook"
                          >
                            FB
                          </a>
                        )}
                        {lead.linkedin && (
                          <a
                            href={lead.linkedin}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-sky-400 hover:text-sky-300 text-[10px] font-bold"
                            title="LinkedIn"
                          >
                            LI
                          </a>
                        )}
                        {lead.twitter && (
                          <a
                            href={lead.twitter}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-text-muted hover:text-white text-[10px] font-bold"
                            title="X/Twitter"
                          >
                            X
                          </a>
                        )}
                      </div>
                    ) : (
                      <span className="text-text-faint text-[10px]">none</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default MapsLeadsTable
