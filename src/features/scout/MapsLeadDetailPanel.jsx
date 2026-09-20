import React, { useState } from "react"
import { Building2, Phone, Mail, Globe, MapPin, Star, Share2, Copy, Check, ExternalLink, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

export function MapsLeadDetailPanel({ lead, onQueueSocials }) {
  const [copiedKey, setCopiedKey] = useState(null)

  if (!lead) {
    return (
      <div className="rounded-[4px] border border-border bg-surface p-6 text-center font-mono text-xs text-text-faint">
        Select a business from the table to view verified contact details, discovered emails, and social links.
      </div>
    )
  }

  const handleCopy = (text, key) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 1500)
  }

  const socialsList = [
    { name: "Instagram", url: lead.instagram, color: "text-pink-400" },
    { name: "Facebook", url: lead.facebook, color: "text-blue-400" },
    { name: "LinkedIn", url: lead.linkedin, color: "text-sky-400" },
    { name: "Twitter / X", url: lead.twitter, color: "text-text" },
  ].filter((s) => Boolean(s.url))

  return (
    <div className="rounded-[4px] border border-border bg-surface p-4 sm:p-5 font-mono text-xs space-y-4">
      {/* Header */}
      <div className="border-b border-border pb-3">
        <div className="flex items-center justify-between gap-2 mb-1">
          <span className="text-[10px] text-text-faint uppercase tracking-wider">
            Business Profile
          </span>
          {lead.rating ? (
            <div className="flex items-center gap-1 text-[11px] bg-[#1a1a24] px-2 py-0.5 rounded border border-border">
              <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
              <span className="font-bold text-white">{lead.rating.toFixed(1)}</span>
              {lead.reviews_count ? (
                <span className="text-text-faint">({lead.reviews_count} reviews)</span>
              ) : null}
            </div>
          ) : null}
        </div>
        <h3 className="text-base font-bold text-white leading-tight">
          {lead.title}
        </h3>
        <p className="text-[11px] text-accent mt-1">
          {lead.category || "Commercial Business"}
        </p>
      </div>

      {/* Address */}
      {lead.address && (
        <div className="space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-text-faint block">
            Location
          </span>
          <div className="flex items-start gap-1.5 text-text-muted">
            <MapPin className="h-3.5 w-3.5 shrink-0 text-text-faint mt-0.5" />
            <span>{lead.address}</span>
          </div>
        </div>
      )}

      {/* Verified Contact Points */}
      <div className="space-y-2.5 pt-1">
        <span className="text-[10px] uppercase tracking-wider text-text-faint block">
          Contact Details
        </span>

        {/* Phone */}
        <div className="flex items-center justify-between rounded bg-[#09090b] p-2 border border-border/60">
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-accent" />
            <span className={lead.phone ? "text-white" : "text-text-faint"}>
              {lead.phone || "No phone listed"}
            </span>
          </div>
          {lead.phone && (
            <button
              type="button"
              onClick={() => handleCopy(lead.phone, "phone")}
              className="text-text-muted hover:text-white"
              title="Copy phone"
            >
              {copiedKey === "phone" ? <Check className="h-3 w-3 text-accent" /> : <Copy className="h-3 w-3" />}
            </button>
          )}
        </div>

        {/* Email */}
        <div className="flex items-center justify-between rounded bg-[#09090b] p-2 border border-border/60">
          <div className="flex items-center gap-2 truncate">
            <Mail className="h-3.5 w-3.5 text-accent shrink-0" />
            <span className={cn("truncate", lead.email ? "text-accent font-semibold" : "text-text-faint")}>
              {lead.email || "No email extracted"}
            </span>
          </div>
          {lead.email && (
            <button
              type="button"
              onClick={() => handleCopy(lead.email, "email")}
              className="text-text-muted hover:text-white shrink-0 ml-1"
              title="Copy email"
            >
              {copiedKey === "email" ? <Check className="h-3 w-3 text-accent" /> : <Copy className="h-3 w-3" />}
            </button>
          )}
        </div>

        {/* Website */}
        <div className="flex items-center justify-between rounded bg-[#09090b] p-2 border border-border/60">
          <div className="flex items-center gap-2 truncate">
            <Globe className="h-3.5 w-3.5 text-text-muted shrink-0" />
            {lead.website ? (
              <a
                href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
                target="_blank"
                rel="noreferrer"
                className="text-white hover:underline truncate"
              >
                {lead.website.replace(/^https?:\/\//, "")}
              </a>
            ) : (
              <span className="text-text-faint">No website</span>
            )}
          </div>
          {lead.website && (
            <a
              href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
              target="_blank"
              rel="noreferrer"
              className="text-text-muted hover:text-white shrink-0 ml-1"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      {/* Discovered Social Profiles */}
      <div className="space-y-2 pt-1 border-t border-border/50">
        <span className="text-[10px] uppercase tracking-wider text-text-faint block">
          Social Presence ({socialsList.length})
        </span>

        {socialsList.length > 0 ? (
          <div className="space-y-1.5">
            {socialsList.map((s) => (
              <a
                key={s.name}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded bg-[#0d0d12] p-2 hover:bg-[#14141c] transition-colors border border-border/40"
              >
                <div className="flex items-center gap-2">
                  <Share2 className="h-3 w-3 text-text-faint" />
                  <span className={cn("font-bold text-[11px]", s.color)}>{s.name}</span>
                </div>
                <ExternalLink className="h-3 w-3 text-text-faint" />
              </a>
            ))}

            {/* Action: Queue socials into Social Scout */}
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => onQueueSocials?.(socialsList.map((s) => s.url))}
              className="w-full mt-2 border-accent/40 text-accent hover:bg-accent/10"
            >
              QUEUE INTO SOCIAL SCOUT
              <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </div>
        ) : (
          <p className="text-[11px] text-text-faint">
            No public social profiles detected on website homepage.
          </p>
        )}
      </div>
    </div>
  )
}

export default MapsLeadDetailPanel
