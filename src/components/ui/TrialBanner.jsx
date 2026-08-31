import { useAuth } from "@/context/AuthContext"
import { Sparkles, ArrowRight, AlertCircle } from "lucide-react"
import { Link } from "react-router-dom"

export function TrialBanner() {
  const { user } = useAuth()

  if (!user || user.role === "admin") {
    return null
  }

  const isTrial = user.plan_id?.startsWith("plan_trial") || user.plan === "trial" || user.trial_active !== undefined
  if (!isTrial) {
    return null
  }

  const daysLeft = user.trial_days_remaining !== undefined ? user.trial_days_remaining : 0
  const usedToday = user.images_used_today || 0
  const dailyLimit = user.images_daily_limit || 5
  const isExpired = daysLeft <= 0 || user.requires_plan

  if (isExpired) {
    return (
      <div className="bg-destructive/15 border-b border-destructive/30 px-4 py-2 flex items-center justify-between text-sm shrink-0 z-20">
        <div className="flex items-center gap-2 text-destructive-foreground font-medium">
          <AlertCircle className="w-4 h-4 text-destructive" />
          <span>Trial ended — select a plan to continue creating AI creatives.</span>
        </div>
        <Link 
          to="/billing" 
          className="flex items-center gap-1.5 font-semibold text-destructive hover:underline transition-colors"
        >
          Select Plan
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    )
  }

  return (
    <div className="bg-primary/10 border-b border-primary/20 px-4 py-2 flex items-center justify-between text-sm shrink-0 z-10">
      <div className="flex items-center gap-2 text-primary-light">
        <Sparkles className="w-4 h-4 text-primary" />
        <span>
          <strong>Trial: {daysLeft} {daysLeft === 1 ? 'day' : 'days'} left</strong> · {usedToday}/{dailyLimit} images today
        </span>
      </div>
      <Link 
        to="/billing" 
        className="flex items-center gap-1.5 font-medium text-primary hover:text-primary-light transition-colors"
      >
        Upgrade Plan
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  )
}
