import { useState, useEffect } from "react"
import { Info, AlertTriangle, CheckCircle2, AlertOctagon, X, ExternalLink } from "lucide-react"
import { updatesService } from "@/services"
import { cn } from "@/lib/utils"

const LEVEL_CONFIG = {
  info: {
    icon: Info,
    barClass: "border-border-strong bg-surface text-text",
    badgeClass: "bg-surface-elevated text-text-muted border-border",
    accentColor: "text-accent",
  },
  warning: {
    icon: AlertTriangle,
    barClass: "border-amber-500/30 bg-amber-950/20 text-amber-200",
    badgeClass: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    accentColor: "text-amber-400",
  },
  success: {
    icon: CheckCircle2,
    barClass: "border-accent/30 bg-accent/5 text-text",
    badgeClass: "bg-accent/10 text-accent border-accent/30",
    accentColor: "text-accent",
  },
  critical: {
    icon: AlertOctagon,
    barClass: "border-red-500/40 bg-red-950/30 text-red-200",
    badgeClass: "bg-red-500/20 text-red-300 border-red-500/40",
    accentColor: "text-red-400",
  },
}

export function UpdatesBanner() {
  const [banner, setBanner] = useState(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function loadBanner() {
      try {
        const data = await updatesService.getBanner()
        if (!isMounted) return
        if (data && data.id) {
          const isDismissed = localStorage.getItem(`helix_banner_dismissed_${data.id}`) === "true"
          if (isDismissed) {
            setDismissed(true)
          } else {
            setBanner(data)
          }
        } else {
          setBanner(null)
        }
      } catch (err) {
        // Silently fail if updates endpoint is temporarily unreachable
        if (isMounted) setBanner(null)
      }
    }

    loadBanner()
    return () => {
      isMounted = false
    }
  }, [])

  if (!banner || dismissed) return null

  const config = LEVEL_CONFIG[banner.level] || LEVEL_CONFIG.info
  const Icon = config.icon

  function handleDismiss() {
    if (banner.id) {
      localStorage.setItem(`helix_banner_dismissed_${banner.id}`, "true")
    }
    setDismissed(true)
  }

  return (
    <aside
      className={cn(
        "relative z-40 flex w-full items-center justify-between border-b px-4 py-2 text-[12px] font-medium transition-all",
        config.barClass
      )}
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-7xl flex-1 items-center justify-center gap-3 pr-6 text-center">
        <span className={cn("flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border", config.badgeClass)}>
          <Icon className={cn("h-3 w-3", config.accentColor)} aria-hidden="true" />
          <span>{banner.level}</span>
        </span>

        <span className="font-semibold tracking-tight text-text">
          {banner.title}
        </span>

        {banner.body && (
          <span className="hidden text-text-muted sm:inline">
            — {banner.body}
          </span>
        )}

        {banner.link_url && (
          <a
            href={banner.link_url}
            target={banner.link_url.startsWith("http") ? "_blank" : "_self"}
            rel={banner.link_url.startsWith("http") ? "noopener noreferrer" : undefined}
            className="inline-flex items-center gap-1 font-mono text-[11px] underline underline-offset-4 text-accent hover:opacity-80 ml-1"
          >
            <span>Learn more</span>
            <ExternalLink className="h-2.5 w-2.5" />
          </a>
        )}
      </div>

      {banner.banner_dismissible && (
        <button
          onClick={handleDismiss}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text rounded transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </aside>
  )
}

export default UpdatesBanner
