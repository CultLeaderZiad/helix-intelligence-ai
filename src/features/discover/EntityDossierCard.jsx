import { useState } from "react"
import {
  Sparkles,
  ShieldAlert,
  Radio,
  Tv,
  Flame,
  BookOpen,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Share2,
  FilterX,
  Target
} from "lucide-react"

export function EntityDossierCard({ profile, query, isZeroResults = false }) {
  const [expanded, setExpanded] = useState(isZeroResults)

  if (!profile) return null

  const {
    entity_name = query,
    entity_type = "general",
    category_label = "Entity Intelligence",
    primary_platforms = [],
    summary = "",
    marketing_archetype = "",
    online_presence = {},
    ad_and_monetization_footprint = {},
    disambiguation = {},
    playbook_and_takeaways = [],
    similar_entities = []
  } = profile

  const isCreator = entity_type === "creator_streamer"
  const hasDisambiguation = disambiguation?.has_confusion

  return (
    <div className="border-b border-border bg-gradient-to-b from-[#14151a] to-[#0d0e12] px-4 py-3.5 transition-all">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="flex items-center gap-1.5 rounded-full border border-[#8b5cf6]/30 bg-[#8b5cf6]/10 px-2.5 py-0.5 text-[11px] font-semibold tracking-wider text-[#a78bfa] uppercase">
            <Sparkles className="size-3 text-[#a78bfa]" />
            {category_label}
          </span>
          <h2 className="text-sm font-semibold tracking-tight text-text">
            {entity_name}
          </h2>
          {marketing_archetype && (
            <span className="hidden rounded bg-surface-elevated/70 px-2 py-0.5 text-[11px] text-text-faint sm:inline-block">
              {marketing_archetype}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Platform Tags */}
          <div className="flex flex-wrap items-center gap-1.5">
            {primary_platforms.map((platform) => (
              <span
                key={platform}
                className="flex items-center gap-1 rounded border border-border/80 bg-surface/80 px-2 py-0.5 text-[10px] font-medium text-text-muted"
              >
                <Radio className="size-2.5 text-accent" />
                {platform}
              </span>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] font-medium text-text-muted hover:bg-surface-elevated hover:text-text transition-colors"
          >
            {expanded ? (
              <>
                <span>Collapse Dossier</span>
                <ChevronUp className="size-3" />
              </>
            ) : (
              <>
                <span>Strategic PR Dossier</span>
                <ChevronDown className="size-3" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Disambiguation Warning / Pruning Notification */}
      {hasDisambiguation && (
        <div className="mt-3 flex items-start gap-2.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-300/90">
          <FilterX className="size-4 shrink-0 text-amber-400 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 font-medium text-amber-300">
              <span>Search Disambiguation:</span>
              <span className="font-semibold text-amber-200">
                {disambiguation.target_intent || entity_name}
              </span>
              <span className="text-amber-400/80">vs.</span>
              <span className="text-amber-400/90 line-through">
                {disambiguation.confused_with || "Phonetic Noise"}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] leading-relaxed text-amber-300/80">
              {disambiguation.explanation ||
                "Ad library phonetic matches were rejected by Helixa's relevance engine to protect intelligence accuracy."}
            </p>
          </div>
        </div>
      )}

      {/* Summary Line */}
      {summary && (
        <p className="mt-2 text-xs leading-relaxed text-text-muted">
          {summary}
        </p>
      )}

      {/* Expanded Intelligence Grid */}
      {expanded && (
        <div className="mt-4 grid grid-cols-1 gap-3.5 pt-3 border-t border-border/60 md:grid-cols-3">
          {/* Column 1: Online Presence & PR Engine */}
          <div className="rounded border border-border/70 bg-surface/50 p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text mb-2">
              <Flame className="size-3.5 text-orange-400" />
              <span>Organic PR & Growth Engine</span>
            </div>
            <div className="space-y-2 text-[11px] text-text-muted">
              <div>
                <span className="font-medium text-text-faint uppercase text-[10px] block mb-0.5">Reach Model</span>
                <p>{online_presence.reach_overview || "Organic short-form video & livestreams"}</p>
              </div>
              <div>
                <span className="font-medium text-text-faint uppercase text-[10px] block mb-0.5">Viral Syndicate Engine</span>
                <p>{online_presence.viral_engine || "Decentralized fan clipping & social syndication"}</p>
              </div>
              <div>
                <span className="font-medium text-text-faint uppercase text-[10px] block mb-0.5">Community Epicenters</span>
                <p>{online_presence.community_hubs || "Livestream chat, X spaces, Discord"}</p>
              </div>
            </div>
          </div>

          {/* Column 2: Ad Footprint & Monetization */}
          <div className="rounded border border-border/70 bg-surface/50 p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text mb-2">
              <DollarSign className="size-3.5 text-emerald-400" />
              <span>Monetization & Ad Footprint</span>
            </div>
            <div className="space-y-2 text-[11px] text-text-muted">
              <div>
                <span className="font-medium text-text-faint uppercase text-[10px] block mb-0.5">Ad Strategy</span>
                <p>{ad_and_monetization_footprint.strategy || (isCreator ? "Does not run self-serve Meta product catalog ads." : "Runs multi-channel performance ads.")}</p>
              </div>
              <div>
                <span className="font-medium text-text-faint uppercase text-[10px] block mb-0.5">Monetization Channels</span>
                <ul className="list-disc pl-3.5 space-y-0.5">
                  {(ad_and_monetization_footprint.primary_monetization || []).map((m, idx) => (
                    <li key={idx}>{m}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Column 3: Actionable Playbook for Marketers */}
          <div className="rounded border border-border/70 bg-surface/50 p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text mb-2">
              <BookOpen className="size-3.5 text-accent" />
              <span>Marketing Takeaways & Playbook</span>
            </div>
            <div className="space-y-2 text-[11px] text-text-muted">
              {(playbook_and_takeaways || []).map((t, idx) => (
                <div key={idx}>
                  <span className="font-medium text-text block mb-0.5">{t.title}</span>
                  <p className="text-[10px] text-text-muted leading-relaxed">{t.detail}</p>
                </div>
              ))}
              {similar_entities.length > 0 && (
                <div className="pt-1 mt-1 border-t border-border/40">
                  <span className="text-[10px] text-text-faint font-medium">Comparable Profiles: </span>
                  <span className="text-[10px] text-text-muted font-mono">{similar_entities.join(", ")}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
