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
  ShieldCheck 
} from "lucide-react"

export function BillingPage() {
  const [billing, setBilling] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchBilling = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await accountService.getBilling()
      setBilling(data)
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
            Real-time balance, active plan entitlements, and your workspace's metered deduction history.
          </p>
        </div>
        <button
          onClick={fetchBilling}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
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
          <div className="text-2xl font-mono font-bold text-amber-300">
            {(billing?.credit_balance || 0).toFixed(1)} <span className="text-xs text-slate-400 font-normal">cr</span>
          </div>
          <p className="text-xs text-slate-500 font-mono">1 credit = $0.01 USD value</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Credits Used</span>
            <Activity className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-slate-200">
            {(billing?.credits_used || 0).toFixed(1)} <span className="text-xs text-slate-400 font-normal">cr</span>
          </div>
          <p className="text-xs text-slate-500 font-mono">Lifetime search consumption</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Trial Window</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-mono font-bold text-cyan-300">
            {billing?.trial_days_remaining !== null && billing?.trial_days_remaining !== undefined
              ? `${billing.trial_days_remaining} days left`
              : "Active"}
          </div>
          <p className="text-xs text-slate-500">
            {billing?.trial_expires_at ? `Expires ${new Date(billing.trial_expires_at).toLocaleDateString()}` : "No expiration"}
          </p>
        </div>
      </div>

      {/* Pricing Rates Info */}
      <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs font-mono text-slate-400">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Execution Rates:</span>
        </div>
        <div>Discover Search: <strong className="text-slate-200">2.0 credits</strong></div>
        <div>Creative Analysis: <strong className="text-slate-200">1.0 credit</strong></div>
        <div>AI Pattern Synthesis: <strong className="text-slate-200">0.5 credits</strong></div>
        <div>Saved Swipe Files: <strong className="text-emerald-400">0.0 credits (Free)</strong></div>
      </div>

      {/* Usage Logs */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
          Your Organization's Metered Deductions History
        </h3>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Operation</th>
                <th className="py-3 px-4">Provider</th>
                <th className="py-3 px-4">Units</th>
                <th className="py-3 px-4 text-right">Credits Deducted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {loading ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-500">
                    Loading usage history...
                  </td>
                </tr>
              ) : (billing?.recent_usage || []).length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-500">
                    No metered operations recorded for this workspace yet.
                  </td>
                </tr>
              ) : (
                billing.recent_usage.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-medium">{log.operation}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] uppercase">
                        {log.provider}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{log.units}</td>
                    <td className="py-3 px-4 text-right font-bold text-amber-300">
                      {log.credits_deducted > 0 ? `-${log.credits_deducted.toFixed(1)}` : `+${Math.abs(log.credits_deducted).toFixed(1)}`} cr
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default BillingPage
