import { useAuth } from "@/context/AuthContext"
import { Sparkles, ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"

export function TrialBanner() {
  const { user } = useAuth()

  // Only show if user is authenticated and has trial days remaining
  if (!user || user.trial_days_remaining === undefined || user.trial_days_remaining === null || user.trial_days_remaining <= 0) {
    return null
  }

  return (
    <div className="bg-primary/10 border-b border-primary/20 px-4 py-2 flex items-center justify-between text-sm shrink-0 z-10">
      <div className="flex items-center gap-2 text-primary-light">
        <Sparkles className="w-4 h-4" />
        <span>
          You have <strong>{user.trial_days_remaining} days left</strong> on your free trial.
        </span>
      </div>
      <Link 
        to="/billing" 
        className="flex items-center gap-1.5 font-medium text-primary hover:text-primary-light transition-colors"
      >
        Upgrade now
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  )
}
