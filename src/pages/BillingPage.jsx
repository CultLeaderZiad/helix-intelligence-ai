import React, { useState, useEffect } from "react"
import { accountService } from "@/services"
import { 
  CreditCard, 
  Coins, 
  Clock, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Zap, 
  ShieldCheck,
  Search,
  Image as ImageIcon,
  MessageSquarePlus
} from "lucide-react"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"

export function BillingPage() {
  const [billing, setBilling] = useState(null)
  const [todayUsage, setTodayUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSupportOpen, setIsSupportOpen] = useState(false)

  const formatLogTime = (val) => {
    if (!val) return "—"
    const cleaned = typeof val === "string" ? val.replace(/\+00:00Z$/, "Z").replace(/\+00:00$/, "Z") : val
    const d = new Date(cleaned)
    return isNaN(d.getTime()) ? "—" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }

  const formatTrialExpiration = (b) => {
    if (b?.plan_type && b.plan_type !== "trial") {
      return "Monthly renewal"
    }
    if (b?.trial_expires_at) {
      const cleaned = typeof b.trial_expires_at === "string" ? b.trial_expires_at.replace(/\+00:00Z$/, "Z").replace(/\+00:00$/, "Z") : b.trial_expires_at
      const d = new Date(cleaned)
      if (!isNaN(d.getTime())) {
        return `Expires ${d.toLocaleDateString()}`
      }
    }
    if (b?.trial_days_remaining !== null && b?.trial_days_remaining !== undefined) {
      return `${b.trial_days_remaining} days remaining`
    }
    return "7-Day Free Trial"
  }

  const fetchBilling = async () => {
    setLoading(true)
    setError(null)
    try {
      const [billingData, usageData] = await Promise.all([
        accountService.getBilling(),
        accountService.getTodayUsage()
      ])
      setBilling(billingData)
      setTodayUsage(usageData)
    } catch (err) {
      setError(err.message || "Failed to load billing information")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBilling()
  }, [])

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <CreditCard className="w-7 h-7 text-indigo-400" />
            Billing & Usage Meter
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time balance, today's metered activity, and your workspace deduction history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsSupportOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition"
          >
            <MessageSquarePlus className="w-3.5 h-3.5 text-teal-400" />
            Report an Issue
          </button>
          <button
            onClick={fetchBilling}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Active Plan</span>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            {billing?.plan_name || "—"}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 uppercase">
              {billing?.plan_type || "trial"}
            </span>
            <span className="text-xs text-emerald-400 font-mono">{billing?.status}</span>
          </div>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Credit Balance</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-amber-400">
            {Number(billing?.credit_balance || 0).toFixed(1)} <span className="text-xs text-slate-400 font-normal">cr</span>
          </div>
          <p className="text-xs text-slate-500">
            {Number(billing?.credits_used || 0).toFixed(1)} total credits consumed
          </p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Daily Quota</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-slate-200">
            {billing?.daily_credits_remaining !== null && billing?.daily_credits_remaining !== undefined
              ? `${Number(billing.daily_credits_remaining || 0).toFixed(1)} cr`
              : "Unlimited"}
          </div>
          <p className="text-xs text-slate-500">
            {Number(billing?.daily_credits_used_today || 0).toFixed(1)} credits used today (UTC)
          </p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Subscription Status</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            {billing?.plan_type === "trial" || !billing?.plan_type
              ? (billing?.trial_days_remaining !== null && billing?.trial_days_remaining !== undefined
                  ? `${billing.trial_days_remaining} days left`
                  : "7 days trial")
              : "Active"}
          </div>
          <p className="text-xs text-slate-500">
            {formatTrialExpiration(billing)}
          </p>
        </div>
      </div>

      {/* Real Daily Usage View Widget */}
      {todayUsage && (
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-400" /> Today's Actual Metered Activity
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              Measured from live database logs
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><Search className="w-3.5 h-3.5 text-teal-400" /> Searches Run</span>
                <span className="font-mono text-white font-bold">{todayUsage.searches_run_today}</span>
              </div>
              <p className="text-[11px] text-slate-500">Live competitor ad scrapes</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><ImageIcon className="w-3.5 h-3.5 text-indigo-400" /> Images / Media</span>
                <span className="font-mono text-white font-bold">{todayUsage.images_generated_today} / {todayUsage.daily_image_limit}</span>
              </div>
              <p className="text-[11px] text-slate-500">AI generative remix outputs</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><Coins className="w-3.5 h-3.5 text-amber-400" /> Credits Deducted</span>
                <span className="font-mono text-amber-400 font-bold">-{Number(todayUsage.credits_consumed_today || 0).toFixed(1)} cr</span>
              </div>
              <p className="text-[11px] text-slate-500">Total metered billing today</p>
            </div>
          </div>
        </div>
      )}

      {/* Pricing Rates Info */}
      <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs font-mono text-slate-400">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Execution Rates:</span>
        </div>
        <div>Discover Search: <strong className="text-slate-200">1.0 credit</strong></div>
        <div>Creative Analysis: <strong className="text-slate-200">0.5 credit</strong></div>
        <div>AI Pattern Synthesis: <strong className="text-slate-200">0.5 credits</strong></div>
        <div>Creative Playbooks: <strong className="text-emerald-400">0.0 credits (Free)</strong></div>
      </div>

      {/* Usage Deduction History */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Recent Metered Deductions
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/20 text-slate-400 font-mono">
                <th className="py-3 px-4 font-semibold">Time</th>
                <th className="py-3 px-4 font-semibold">Provider</th>
                <th className="py-3 px-4 font-semibold">Operation</th>
                <th className="py-3 px-4 font-semibold text-right">Units</th>
                <th className="py-3 px-4 font-semibold text-right">Credits Deducted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500 font-mono">
                    Loading deduction history...
                  </td>
                </tr>
              ) : (billing?.recent_logs || []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500 font-mono">
                    No usage deductions logged yet.
                  </td>
                </tr>
              ) : (
                (billing?.recent_logs || []).map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30 transition font-mono">
                    <td className="py-3 px-4 text-slate-400">{formatLogTime(log.created_at)}</td>
                    <td className="py-3 px-4 text-slate-300">{log.provider}</td>
                    <td className="py-3 px-4 text-slate-300">{log.operation}</td>
                    <td className="py-3 px-4 text-right text-slate-400">{log.units}</td>
                    <td className="py-3 px-4 text-right text-indigo-400 font-bold">-{Number(log.credits_deducted || 0).toFixed(1)} cr</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <SupportFeedbackModal
        isOpen={isSupportOpen}
        onClose={() => setIsSupportOpen(false)}
        initialContext={{ page: "Billing & Meter", plan: billing?.plan_name || "Trial", tag: "billing" }}
      />
    </div>
  )
}

export default BillingPage
