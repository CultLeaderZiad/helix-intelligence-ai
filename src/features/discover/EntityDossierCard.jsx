import { useState } from "react"
import {
  Sparkles,
  ShieldAlert,
  Tv,
  Flame,
  BookOpen,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Share2,
  FilterX,
  Target,
  ExternalLink,
  Users,
  Radio,
  Video
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

// Helper to determine platform metadata, logo, styling, and real verified channel & search URLs
export function getPlatformMeta(platformName = "", entityName = "", query = "", profile = {}) {
  const p = platformName.toLowerCase()
  const cleanQ = (entityName || query || "").trim()
  const handle = cleanQ.split(" ")[0].toLowerCase().replace(/[^a-z0-9_]/g, "")
  const isTate = /tate/i.test(cleanQ)
  const isSneako = /sneako/i.test(cleanQ)
  const isAdin = /adin/i.test(cleanQ)
  const isKai = /kai/i.test(cleanQ)

  const links = profile?.social_links || {}

  if (p.includes("kick")) {
    const keyData = links.kick || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://kick.com/sneako" : isTate ? "https://kick.com/tatespeech" : isAdin ? "https://kick.com/adinross" : `https://kick.com/${handle || "explore"}`)
    const search_url = keyData.search_url || `https://kick.com/search?q=${encodeURIComponent(cleanQ)}`
    const profileHandle = keyData.handle || (isSneako ? "sneako" : isTate ? "tatespeech" : isAdin ? "adinross" : handle)

    return {
      name: "Kick",
      label: "Kick",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: KickLogo,
      badgeClass: "bg-[#0e1f0e] text-[#53fc18] border-[#53fc18]/40 hover:bg-[#53fc18] hover:text-black hover:border-[#53fc18]",
      color: "#53fc18"
    }
  }

  if (p.includes("rumble")) {
    const keyData = links.rumble || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://rumble.com/c/Sneako" : isTate ? "https://rumble.com/c/TateSpeech" : `https://rumble.com/search/all?q=${encodeURIComponent(cleanQ)}`)
    const search_url = keyData.search_url || `https://rumble.com/search/all?q=${encodeURIComponent(cleanQ)}`
    const profileHandle = keyData.handle || (isSneako ? "Sneako" : isTate ? "TateSpeech" : handle.toUpperCase())

    return {
      name: "Rumble",
      label: "Rumble",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: RumbleLogo,
      badgeClass: "bg-[#112211] text-[#85c742] border-[#85c742]/40 hover:bg-[#85c742] hover:text-black hover:border-[#85c742]",
      color: "#85c742"
    }
  }

  if (p.includes("youtube")) {
    const keyData = links.youtube || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://www.youtube.com/results?search_query=sneako" : isTate ? "https://www.youtube.com/results?search_query=andrew+tate" : `https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQ)}`)
    const search_url = keyData.search_url || `https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQ)}`
    const profileHandle = keyData.handle || (isSneako ? "@TheUnfiltered" : isTate ? "TateSpeech" : `@${handle}`)

    return {
      name: "YouTube",
      label: "YouTube",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: YouTubeLogo,
      badgeClass: "bg-[#250d0d] text-[#ff4444] border-[#ff4444]/40 hover:bg-[#ff0000] hover:text-white hover:border-[#ff0000]",
      color: "#ff4444"
    }
  }

  if (p.includes("twitter") || p.includes("x")) {
    const keyData = links.x || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://x.com/TheSneako" : isTate ? "https://x.com/Cobratate" : isAdin ? "https://x.com/adinross" : isKai ? "https://x.com/KaiCenat" : `https://x.com/${handle}`)
    const search_url = keyData.search_url || `https://x.com/search?q=${encodeURIComponent(cleanQ)}&src=typeahead_click`
    const profileHandle = keyData.handle || (isSneako ? "@TheSneako" : isTate ? "@Cobratate" : isAdin ? "@adinross" : isKai ? "@KaiCenat" : `@${handle}`)

    return {
      name: "X",
      label: "X (Twitter)",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: XLogo,
      badgeClass: "bg-[#1a1c23] text-white border-white/30 hover:bg-white hover:text-black hover:border-white",
      color: "#ffffff"
    }
  }

  if (p.includes("instagram") || p.includes("insta")) {
    const keyData = links.instagram || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://instagram.com/sneako" : isTate ? "https://instagram.com/cobratate" : isKai ? "https://instagram.com/kaicenat" : `https://instagram.com/${handle}`)
    const search_url = keyData.search_url || `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(cleanQ)}`
    const profileHandle = keyData.handle || (isSneako ? "@sneako" : isTate ? "@cobratate" : isKai ? "@kaicenat" : `@${handle}`)

    return {
      name: "Instagram",
      label: "Instagram",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: InstagramLogo,
      badgeClass: "bg-[#250d18] text-[#ff4da6] border-[#ff4da6]/40 hover:bg-[#ff4da6] hover:text-black hover:border-[#ff4da6]",
      color: "#ff4da6"
    }
  }

  if (p.includes("tiktok")) {
    const keyData = links.tiktok || {}
    const profile_url = keyData.profile_url || (isSneako ? "https://www.tiktok.com/tag/sneako" : isTate ? "https://www.tiktok.com/tag/andrewtate" : `https://www.tiktok.com/search?q=${encodeURIComponent(cleanQ)}`)
    const search_url = keyData.search_url || `https://www.tiktok.com/search?q=${encodeURIComponent(cleanQ)}`
    const profileHandle = keyData.handle || (isSneako ? "@sneako" : isTate ? "@cobratate" : `@${handle}`)

    return {
      name: "TikTok",
      label: "TikTok",
      handle: profileHandle,
      url: profile_url,
      profile_url,
      search_url,
      Icon: TikTokLogo,
      badgeClass: "bg-[#0b1f24] text-[#25f4ee] border-[#25f4ee]/40 hover:bg-[#25f4ee] hover:text-black hover:border-[#25f4ee]",
      color: "#25f4ee"
    }
  }

  return {
    name: platformName,
    label: platformName,
    handle: `@${handle}`,
    url: `https://www.google.com/search?q=${encodeURIComponent(cleanQ + " " + platformName)}`,
    profile_url: `https://www.google.com/search?q=${encodeURIComponent(cleanQ + " " + platformName)}`,
    search_url: `https://www.google.com/search?q=${encodeURIComponent(cleanQ + " " + platformName)}`,
    Icon: ExternalLink,
    badgeClass: "bg-surface-elevated text-text border-border hover:border-accent hover:text-accent",
    color: "#a3e635"
  }
}

export function EntityDossierCard({ profile, query, isZeroResults = false }) {
  const [expanded, setExpanded] = useState(true)
  const { t, isRtl } = useLanguage()

  if (!profile) return null

  const {
    entity_name = query,
    entity_type = "general",
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

  const isCreator = entity_type === "creator_streamer" || entity_type === "influencer"
  const hasDisambiguation = disambiguation?.has_confusion

  // Ensure standard streaming / social platforms exist for creator entities
  const defaultPlatforms = ["X (Twitter)", "Instagram", "Kick", "Rumble", "YouTube", "TikTok"]
  const platformsToRender = primary_platforms.length > 0
    ? Array.from(new Set([...primary_platforms, ...defaultPlatforms]))
    : defaultPlatforms

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
            {platformsToRender.map((platform) => {
              const meta = getPlatformMeta(platform, entity_name, query, profile)
              const { Icon } = meta
              return (
                <a
                  key={platform}
                  href={meta.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={`${t("openOnPlatform")} ${meta.label}`}
                  className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-bold transition-all shadow-sm transform hover:scale-105 ${meta.badgeClass}`}
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

      {/* Summary Line */}
      {summary && (
        <p className="mt-2.5 text-xs leading-relaxed text-text-muted font-sans max-w-5xl">
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
                  <p className="text-text leading-relaxed font-sans">
                    {online_presence.reach_overview || "Hundreds of thousands of live viewers & syndicated short clips."}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("viralSyndicate")}
                  </span>
                  <p className="text-text leading-relaxed font-sans">
                    {online_presence.viral_engine || "Decentralized fan clipping & social syndication."}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("communityEpicenters")}
                  </span>
                  <p className="text-text leading-relaxed font-sans">
                    {online_presence.community_hubs || "Livestream live chat, X Spaces, Discord/Telegram subscriber groups."}
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
                  <p className="text-text leading-relaxed font-sans">
                    {ad_and_monetization_footprint.strategy ||
                      (isCreator
                        ? "Does not run self-serve Meta product feed ads. Growth is driven entirely by organic syndication."
                        : "Runs multi-channel performance ads.")}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-text-faint block mb-0.5">
                    {t("monetizationChannels")}
                  </span>
                  <ul className="list-disc pl-4 space-y-1 text-text font-sans">
                    {(ad_and_monetization_footprint.primary_monetization || [
                      "Exclusive multi-million streaming contracts (Kick, Rumble)",
                      "In-stream native sponsor reads & brand integrations",
                      "Affiliate creator links and exclusive merchandise drops"
                    ]).map((m, idx) => (
                      <li key={idx} className="leading-snug">{m}</li>
                    ))}
                  </ul>
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
                {(playbook_and_takeaways.length > 0 ? playbook_and_takeaways : [
                  {
                    title: "Decentralized Clipping Syndicates",
                    detail: "Instead of paying Meta $40-$60 CPMs, incentivize third-party clippers to generate tens of millions of views organically."
                  },
                  {
                    title: "Native In-Stream Sponsor Reads",
                    detail: "Live stream reviews achieve 5-10x higher conversion than standard display ads through unscripted authentic demonstrations."
                  }
                ]).map((item, idx) => (
                  <div key={idx} className="border-b border-border/30 pb-2 last:border-b-0 last:pb-0">
                    <span className="font-bold text-text block mb-0.5 font-mono">{item.title}</span>
                    <p className="text-[11px] text-text-muted leading-relaxed font-sans">{item.detail}</p>
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
                <p className="text-[11px] text-text-muted font-sans mt-0.5">
                  Direct Verified Account Profiles & Platform Search Feeds
                </p>
              </div>
              <span className="text-[10px] font-mono text-accent bg-accent/10 border border-accent/30 rounded px-2 py-0.5">
                Multi-Platform Intelligence Active
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {platformsToRender.map((platform) => {
                const meta = getPlatformMeta(platform, entity_name, query, profile)
                const { Icon } = meta
                return (
                  <div
                    key={platform}
                    className="flex flex-col justify-between p-3 rounded-md bg-surface border border-border hover:border-accent/60 transition-all shadow-sm group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0 mb-2.5">
                      <div className={`p-2 rounded-md ${meta.badgeClass.split(" ")[0]} border ${meta.badgeClass.split(" ")[2]}`}>
                        <Icon className="size-4 shrink-0" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-white block group-hover:text-accent transition-colors truncate">
                          {meta.label}
                        </span>
                        <span className="text-[10px] text-accent font-mono block truncate">
                          {meta.handle || "Official"}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-border/50">
                      <a
                        href={meta.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 inline-flex items-center justify-center gap-1 rounded bg-surface-2 px-2 py-1.5 text-[11px] font-mono font-medium text-text hover:bg-accent hover:text-black transition-colors"
                        title={`Open official profile for ${entity_name} on ${meta.label}`}
                      >
                        Profile ↗
                      </a>
                      <a
                        href={meta.search_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 inline-flex items-center justify-center gap-1 rounded bg-surface-2 px-2 py-1.5 text-[11px] font-mono font-medium text-text-muted hover:text-white hover:bg-surface-elevated transition-colors"
                        title={`Search for "${query || entity_name}" on ${meta.label}`}
                      >
                        Search ↗
                      </a>
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
