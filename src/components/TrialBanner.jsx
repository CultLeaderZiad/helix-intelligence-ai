import { Link } from "react-router-dom"
import { Clock } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"

const DAY_MS = 24 * 60 * 60 * 1000

const COPY = {
  en: {
    left: (n) => (n === 1 ? "Your free access ends in 1 day." : `Your free access ends in ${n} days.`),
    today: "Your free access ends today.",
    ended: "Your access has ended. Your saved ads, boards and searches are kept.",
    pending: "Your workspace is waiting for access.",
    cta: "Access & usage",
  },
  ar: {
    left: (n) => (n === 1 ? "ينتهي وصولك المجاني بعد يوم واحد." : `ينتهي وصولك المجاني بعد ${n} أيام.`),
    today: "ينتهي وصولك المجاني اليوم.",
    ended: "انتهى وصولك. إعلاناتك ولوحاتك وعمليات بحثك المحفوظة باقية.",
    pending: "مساحة عملك بانتظار الوصول.",
    cta: "الوصول والاستخدام",
  },
}

/**
 * What the banner should say, or null for nothing. Pure for tests.
 * Shown only while access is time-limited (the 7-day trial or an admin end
 * date), and after it has ended. Admins and open-ended access see nothing.
 */
export function trialBannerState(user, now = Date.now()) {
  if (!user || user.is_platform_admin) return null
  const status = user.access_status
  if (status === "expired" || status === "revoked") return { kind: "ended" }
  if (status !== "approved" || !user.access_expires_at) return null
  const ms = new Date(user.access_expires_at).getTime() - now
  if (Number.isNaN(ms)) return null
  if (ms <= 0) return { kind: "ended" }
  const days = Math.ceil(ms / DAY_MS)
  if (days > 7) return null
  return ms < DAY_MS ? { kind: "today" } : { kind: "left", days }
}

export function TrialBanner() {
  const { user } = useAuth()
  const { lang } = useLanguage()
  const state = trialBannerState(user)
  if (!state) return null
  const c = COPY[lang === "ar" ? "ar" : "en"]
  const text = state.kind === "left" ? c.left(state.days) : c[state.kind]
  const ended = state.kind === "ended"
  return (
    <div
      role="status"
      className={`flex shrink-0 items-center justify-between gap-3 border-b px-4 py-1.5 text-xs ${
        ended ? "border-warning/40 bg-warning/10 text-text" : "border-border bg-surface-2 text-text-muted"
      }`}
    >
      <span className="flex items-center gap-2">
        <Clock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {text}
      </span>
      <Link to="/access" className="shrink-0 font-medium text-accent hover:underline">
        {c.cta}
      </Link>
    </div>
  )
}
