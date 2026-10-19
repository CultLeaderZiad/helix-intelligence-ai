import { useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { accountService } from "@/services"
import { Sparkles, ArrowRight, AlertCircle } from "lucide-react"
import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"

export function TrialBanner() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const [access, setAccess] = useState(null)

  useEffect(() => {
    if (!user || user.role === "admin") return undefined
    let alive = true
    accountService.getAccess()
      .then((row) => {
        if (alive) setAccess(row)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [user?.id, user?.role])

  if (!user || user.role === "admin") {
    return null
  }

  const isTrial = user.plan_id?.startsWith("plan_trial") || user.plan === "trial" || user.trial_active !== undefined
  const accessMessage = access?.status && access.status !== "approved"
    ? t({
        pending: "accessPendingMessage",
        rejected: "accessRejectedMessage",
        expired: "accessExpiredMessage",
        revoked: "accessRevokedMessage",
      }[access.status] || "accessPendingMessage")
    : null
  if (!isTrial && !accessMessage) {
    return null
  }

  const daysLeft = user.trial_days_remaining !== undefined ? user.trial_days_remaining : 0
  const usedToday = user.images_used_today || 0
  const dailyLimit = user.images_daily_limit ?? 5
  const isExpired = daysLeft <= 0 || user.requires_plan

  if (isExpired) {
    return (
      <div className="bg-destructive/15 border-b border-destructive/30 px-4 py-2 flex items-center justify-between text-sm shrink-0 z-20">
        <div className="flex items-center gap-2 text-destructive-foreground font-medium">
          <AlertCircle className="w-4 h-4 text-destructive" />
          <span dir="auto">{accessMessage || t("trialEndedRequest")}</span>
        </div>
        <Link 
          to="/billing" 
          className="flex items-center gap-1.5 font-semibold text-destructive hover:underline transition-colors"
        >
          {t("requestAccess")}
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    )
  }

  return (
    <div className="bg-primary/10 border-b border-primary/20 px-4 py-2 flex items-center justify-between text-sm shrink-0 z-10">
      <div className="flex items-center gap-2 text-primary-light">
        <Sparkles className="w-4 h-4 text-primary" />
        <span dir="auto">
          <strong>{t("trialDaysLeft").replace("{days}", String(daysLeft))}</strong> · {t("imagesToday").replace("{used}", String(usedToday)).replace("{limit}", String(dailyLimit))}
          {accessMessage ? ` · ${accessMessage}` : ""}
        </span>
      </div>
      <Link 
        to="/billing" 
        className="flex items-center gap-1.5 font-medium text-primary hover:text-primary-light transition-colors"
      >
        {t("requestAccess")}
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  )
}
