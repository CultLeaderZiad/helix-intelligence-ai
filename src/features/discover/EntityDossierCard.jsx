import { useState } from "react"
import {
  Sparkles,
  Flame,
  BookOpen,
  ChevronDown,
  ChevronUp,
  DollarSign,
  FilterX,
  ExternalLink,
  Radio,
} from "lucide-react"
import { useLanguage } from "@/context/LanguageContext"

// Official Branded Platform Logos
export function KickLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M3 2h5v6h3V5h5V2h5v8h-3v3h-3v3h3v3h3v8h-5v-3h-5v-3h-3v6H3V2z" />
    </svg>
  )
}

export function RumbleLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.8 7.3c-.3-.8-1-1.3-1.8-1.3H7c-.8 0-1.5.5-1.8 1.3L3.2 13c-.3.8-.1 1.7.5 2.2l4.3 3.8c.4.4 1 .6 1.5.6h5c.6 0 1.1-.2 1.5-.6l4.3-3.8c.6-.5.8-1.4.5-2.2l-2-5.7zM9.5 14.5l5-3.5-5-3.5v7z" />
    </svg>
  )
}

export function YouTubeLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  )
}

export function XLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export function InstagramLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
    </svg>
  )
}

export function TikTokLogo({ className = "size-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.24 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
    </svg>
  )
}

const PLATFORM_STYLES = {
  kick: {
    name: "Kick",
    label: "Kick",
    Icon: KickLogo,
    badgeClass: "bg-[#0e1f0e] text-[#53fc18] border-[#53fc18]/40",
    color: "#53fc18",
  },
  rumble: {
    name: "Rumble",
    label: "Rumble",
    Icon: RumbleLogo,
    badgeClass: "bg-[#112211] text-[#85c742] border-[#85c742]/40",
    color: "#85c742",
  },
  youtube: {
    name: "YouTube",
    label: "YouTube",
    Icon: YouTubeLogo,
    badgeClass: "bg-[#250d0d] text-[#ff4444] border-[#ff4444]/40",
    color: "#ff4444",
  },
  x: {
    name: "X",
    label: "X (Twitter)",
    Icon: XLogo,
    badgeClass: "bg-[#1a1c23] text-white border-white/30",
    color: "#ffffff",
  },
  instagram: {
    name: "Instagram",
    label: "Instagram",
    Icon: InstagramLogo,
    badgeClass: "bg-[#250d18] text-[#ff4da6] border-[#ff4da6]/40",
    color: "#ff4da6",
  },
  tiktok: {
    name: "TikTok",
    label: "TikTok",
    Icon: TikTokLogo,
    badgeClass: "bg-[#0b1f24] text-[#25f4ee] border-[#25f4ee]/40",
    color: "#25f4ee",
  },
}

function platformKey(platformName = "") {
  const p = platformName.toLowerCase()
  if (p.includes("kick")) return "kick"
  if (p.includes("rumble")) return "rumble"
  if (p.includes("youtube")) return "youtube"
  if (p.includes("twitter") || p === "x" || p.includes("x (")) return "x"
  if (p.includes("instagram") || p.includes("insta")) return "instagram"
  if (p.includes("tiktok")) return "tiktok"
  return null
}

function httpUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null
  try {
    const url = new URL(value.trim())
    if (url.protocol !== "https:" && url.protocol !== "http:") return null
    return url.toString()
  } catch {
    return null
  }
}

function evidenceText(profile, t) {
  const labels = {
    curated_unverified: "evidenceCurated",
    model_hypothesis: "evidenceHypothesis",
    unverified_heuristic: "evidenceHeuristic",
    fetched: "evidenceFetched",
  }
  const key = labels[profile?.evidence_status]
  return key ? t(key) : null
}

// Styling only. A profile or search URL is used when that social link was fetched.
export function getPlatformMeta(platformName = "", _entityName = "", _query = "", profile = {}) {
  const key = platformKey(platformName)
  const style = key
    ? PLATFORM_STYLES[key]
    : {
        name: platformName || "Profile",
        label: platformName || "Profile",
        Icon: ExternalLink,
        badgeClass: "bg-surface-elevated text-text border-border",
        color: "#a3e635",
      }
  const entry = key && profile?.social_links?.[key] && typeof profile.social_links[key] === "object"
    ? profile.social_links[key]
    : null
  const fetched = entry?.fetched === true
  const profileUrl = fetched ? httpUrl(entry.profile_url) : null
  const searchUrl = fetched ? httpUrl(entry.search_url) : null
  const handle = typeof entry?.handle === "string" ? entry.handle : ""

  return {
    name: style.name,
    label: style.label,
    handle,
    fetched: Boolean(profileUrl),
    url: profileUrl,
    profile_url: profileUrl,
    search_url: searchUrl,
    Icon: style.Icon,
    badgeClass: style.badgeClass,
    color: style.color,
  }
}

export function EntityDossierCard({ profile, query, isZeroResults = false }) {
  const [expanded, setExpanded] = useState(true)
  const { t } = useLanguage()

  if (!profile) return null

  const {
    entity_name = query,
    category_label = "Entity Intelligence",
    primary_platforms = ["Kick", "Rumble", "YouTube", "X (Twitter)"],
    summary = "",
    marketing_archetype = "",
    online_presence = {},
    ad_and_monetization_footprint = {},
    disambiguation = {},
    playbook_and_takeaways = [],
    similar_entities = []
  } = profile

  const hasDisambiguation = disambiguation?.has_confusion
  const note = evidenceText(profile, t)
  const listed = (Array.isArray(primary_platforms) ? primary_platforms : []).filter(
    (name) => typeof name === "string" && name.trim()
  )
  const fromLinks = Object.entries(profile?.social_links || {})
    .filter(([, entry]) => entry && typeof entry === "object")
    .map(([key, entry]) => (typeof entry.name === "string" && entry.name.trim() ? entry.name : key))
  const platformsToRender = []
  const seenPlatforms = new Set()
  for (const name of [...listed, ...fromLinks]) {
    const id = platformKey(name) || name.toLowerCase()
    if (seenPlatforms.has(id)) continue
    seenPlatforms.add(id)
    platformsToRender.push(name)
  }

  return (
    <div className="border-b border-border bg-gradient-to-b from-[#14161f] via-[#0f1016] to-[#0a0b0e] px-4 py-3.5 transition-all text-text">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="flex items-center gap-1.5 rounded-full border border-[#8b5cf6]/40 bg-[#8b5cf6]/15 px-3 py-1 text-xs font-bold tracking-wider text-[#c4b5fd] uppercase shadow-sm">
            <Sparkles className="size-3.5 text-[#a78bfa] animate-pulse" />
            {category_label}
          </span>
          <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
            {entity_name}
          </h2>
          {marketing_archetype && (
            <span className="hidden rounded bg-surface-elevated/80 border border-border/50 px-2.5 py-0.5 text-xs text-text-muted sm:inline-block font-mono">
              {marketing_archetype}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Prominent Branded Platform Links with Official Logos */}
          <div className="flex flex-wrap items-center gap-2">
            {platformsToRender.length === 0 ? (
              <span className="text-xs text-text-muted" dir="auto">{t("profileUnavailable")}</span>
            ) : platformsToRender.map((platform) => {
              const meta = getPlatformMeta(platform, entity_name, query, profile)
              const { Icon } = meta
              if (!meta.profile_url) {
                return (
                  <span
                    key={platform}
                    dir="auto"
                    className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-bold ${meta.badgeClass}`}
                  >
                    <Icon className="size-3.5 shrink-0" />
                    <span>{meta.label}</span>
                    <span className="font-normal opacity-80">{t("profileUnavailable")}</span>
                  </span>
                )
              }
              return (
                <a
                  key={platform}
                  href={meta.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={`${t("openOnPlatform")} ${meta.label}`}
                  className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-bold transition-all shadow-sm ${meta.badgeClass}`}
                >
                  <Icon className="size-3.5 shrink-0" />
                  <span>{meta.label}</span>
                  <ExternalLink className="size-3 opacity-60 ml-0.5" />
                </a>
              )
            })}
          </div>

          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-text hover:bg-surface-elevated hover:border-accent/50 transition-colors shadow-sm ml-1"
          >
            {expanded ? (
              <>
                <span>{t("collapseDossier")}</span>
                <ChevronUp className="size-3.5" />
              </>
            ) : (
              <>
                <span>{t("dossierTitle")}</span>
                <ChevronDown className="size-3.5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Disambiguation Warning / Pruning Notification */}
      {hasDisambiguation && (
        <div className="mt-3 flex items-start gap-2.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-200">
          <FilterX className="size-4 shrink-0 text-amber-400 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5 font-medium text-amber-300">
              <span className="font-bold">{t("disambiguationLabel")}:</span>
              <span className="font-bold text-amber-100 bg-amber-500/20 px-1.5 py-0.5 rounded">
                {disambiguation.target_intent || entity_name}
              </span>
              <span className="text-amber-400/80 font-mono">vs.</span>
              <span className="text-amber-400/90 line-through">
                {disambiguation.confused_with || t("phoneticNoise")}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-amber-200/90 font-sans">
              {disambiguation.explanation ||
                "Ad library phonetic matches were rejected by Helixa's relevance engine to protect intelligence accuracy."}
            </p>
          </div>
        </div>
      )}

      {note ? (
        <p className="mt-2 text-[11px] leading-relaxed text-text-muted" dir="auto">
          {note}
        </p>
      ) : null}

      {/* Summary Line */}
      {summary && (
        <p className="mt-2.5 text-xs leading-relaxed text-text-muted font-sans max-w-5xl" dir="auto">
          {summary}
        </p>
      )}

      {/* Expanded Intelligence Grid */}
      {expanded && (
        <div className="mt-4 space-y-3.5 border-t border-border/60 pt-3.5">
          {/* Main 3-Column Intelligence Matrix */}
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
            {/* Column 1: Online Presence & PR Engine */}
            <div className="rounded-lg border border-border/80 bg-surface/70 p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white mb-2.5 pb-1.5 border-b border-border/50">
                <Flame className="size-4 text-orange-400" />
                <span>{t("organicPrEngine")}</span>
              </div>
              <div className="space-y-2.5 text-xs text-text-muted">
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("reachModel")}
                  </span>
                  <p className="text-text leading-relaxed font-sans" dir="auto">
                    {online_presence.reach_overview || t("unavailable")}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("viralSyndicate")}
                  </span>
                  <p className="text-text leading-relaxed font-sans" dir="auto">
                    {online_presence.viral_engine || t("unavailable")}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("communityEpicenters")}
                  </span>
                  <p className="text-text leading-relaxed font-sans" dir="auto">
                    {online_presence.community_hubs || t("unavailable")}
                  </p>
                </div>
              </div>
            </div>

            {/* Column 2: Ad Footprint & Monetization */}
            <div className="rounded-lg border border-border/80 bg-surface/70 p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white mb-2.5 pb-1.5 border-b border-border/50">
                <DollarSign className="size-4 text-emerald-400" />
                <span>{t("monetizationFootprint")}</span>
              </div>
              <div className="space-y-2.5 text-xs text-text-muted">
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("adStrategy")}
                  </span>
                  <p className="text-text leading-relaxed font-sans" dir="auto">
                    {ad_and_monetization_footprint.strategy || t("unavailable")}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("monetizationChannels")}
                  </span>
                  {(ad_and_monetization_footprint.primary_monetization || []).length === 0 ? (
                    <p className="text-text font-sans" dir="auto">{t("unavailable")}</p>
                  ) : (
                    <ul className="list-disc pl-4 space-y-1 text-text font-sans">
                      {ad_and_monetization_footprint.primary_monetization.map((m, idx) => (
                        <li key={idx} className="leading-snug" dir="auto">{m}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>

            {/* Column 3: Actionable Playbook for Marketers */}
            <div className="rounded-lg border border-border/80 bg-surface/70 p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white mb-2.5 pb-1.5 border-b border-border/50">
                <BookOpen className="size-4 text-accent" />
                <span>{t("marketingTakeaways")}</span>
              </div>
              <div className="space-y-2.5 text-xs text-text-muted">
                {playbook_and_takeaways.length === 0 ? (
                  <p className="text-text font-sans" dir="auto">{t("unavailable")}</p>
                ) : playbook_and_takeaways.map((item, idx) => (
                  <div key={idx} className="border-b border-border/30 pb-2 last:border-b-0 last:pb-0">
                    <span className="font-bold text-text block mb-0.5 font-mono">{item.title}</span>
                    <p className="text-[11px] text-text-muted leading-relaxed font-sans" dir="auto">{item.detail}</p>
                  </div>
                ))}
                {similar_entities.length > 0 && (
                  <div className="pt-2 mt-1 border-t border-border/40">
                    <span className="text-[10px] text-text-faint font-mono uppercase font-bold">
                      {t("comparableProfiles")}:{" "}
                    </span>
                    <span className="text-[11px] text-accent font-semibold">{similar_entities.join(" · ")}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Platform Stream & Channel Hub Section */}
          <div className="rounded-lg border border-border/90 bg-[#12141c] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div>
                <h3 className="text-xs font-bold text-white font-mono flex items-center gap-2">
                  <Radio className="size-3.5 text-accent animate-pulse" />
                  {t("creatorHubTitle")}
                </h3>
                <p className="text-[11px] text-text-muted font-sans mt-0.5" dir="auto">
                  {t("creatorHubSubtitle")}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {platformsToRender.length === 0 ? (
                <p className="text-xs text-text-muted" dir="auto">{t("profileUnavailable")}</p>
              ) : platformsToRender.map((platform) => {
                const meta = getPlatformMeta(platform, entity_name, query, profile)
                const { Icon } = meta
                const handleLabel = meta.handle || t("profileUnavailable")
                return (
                  <div
                    key={platform}
                    className="flex flex-col justify-between p-3 rounded-md bg-surface border border-border shadow-sm"
                  >
                    <div className="flex items-center gap-2.5 min-w-0 mb-2.5">
                      <div className={`p-2 rounded-md ${meta.badgeClass.split(" ")[0]} border ${meta.badgeClass.split(" ")[2]}`}>
                        <Icon className="size-4 shrink-0" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-white block truncate">
                          {meta.label}
                        </span>
                        <span className="text-[10px] text-text-muted font-mono block truncate" dir="auto">
                          {handleLabel}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-border/50">
                      {meta.profile_url ? (
                        <a
                          href={meta.profile_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 inline-flex items-center justify-center gap-1 rounded bg-surface-2 px-2 py-1.5 text-[11px] font-mono font-medium text-text hover:bg-accent hover:text-black transition-colors"
                        >
                          {t("openOnPlatform")} ↗
                        </a>
                      ) : (
                        <span className="flex-1 inline-flex items-center justify-center rounded bg-surface-2 px-2 py-1.5 text-[11px] font-mono text-text-muted" dir="auto">
                          {t("profileUnavailable")}
                        </span>
                      )}
                      {meta.search_url ? (
                        <a
                          href={meta.search_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 inline-flex items-center justify-center gap-1 rounded bg-surface-2 px-2 py-1.5 text-[11px] font-mono font-medium text-text-muted hover:text-white hover:bg-surface-elevated transition-colors"
                        >
                          {t("searchLabel")} ↗
                        </a>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EntityDossierCard
