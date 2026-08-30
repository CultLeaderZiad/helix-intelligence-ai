import React, { useState, useEffect } from "react"
import { adminService } from "@/services"
import { 
  Gauge, 
  DollarSign, 
  Coins, 
  Activity, 
  Cpu, 
  Globe, 
  Sparkles, 
  RefreshCw,
  Search
} from "lucide-react"

export function UsagePage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterProvider, setFilterProvider] = useState("all")

  const fetchUsage = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminService.getUsageSummary()
      setSummary(data)
    } catch (err) {
      setError(err.message || "Failed to load usage data")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsage()
  }, [])

  const logs = summary?.recent_logs || []
  const filteredLogs = filterProvider === "all" 
    ? logs 
    : logs.filter((l) => l.provider.toLowerCase() === filterProvider.toLowerCase())

  const getProviderIcon = (provider) => {
    switch (provider.toLowerCase()) {
      case "groq":
        return <Cpu className="w-4 h-4 text-emerald-400" />
      case "brightdata":
        return <Globe className="w-4 h-4 text-cyan-400" />
      case "scrapegraph":
        return <Sparkles className="w-4 h-4 text-amber-400" />
      default:
        return <Activity className="w-4 h-4 text-indigo-400" />
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Gauge className="w-7 h-7 text-indigo-400" />
            Global Usage & Provider Metering
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real provider spend tracking and credit deductions across all organizations.
          </p>
        </div>
        <button
          onClick={fetchUsage}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Total Provider Cost (USD)</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-emerald-400 mt-2">
            ${(summary?.total_cost_usd || 0).toFixed(4)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Direct third-party API spend</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Total Credits Deducted</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-amber-400 mt-2">
            {(summary?.total_credits_deducted || 0).toFixed(1)} cr
          </div>
          <p className="text-xs text-slate-500 mt-1">Across all tenant search passes</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Total Metered Operations</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-slate-200 mt-2">
            {summary?.total_requests || 0}
          </div>
          <p className="text-xs text-slate-500 mt-1">Logged pipeline & AI executions</p>
        </div>
      </div>

      {/* Provider Breakdown Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
          Spend & Quotas by Provider
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {summary?.by_provider?.map((p, idx) => (
            <div key={idx} className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5 uppercase font-mono">
                  {getProviderIcon(p.provider)}
                  {p.provider}
                </span>
                <span className="text-[11px] font-mono text-slate-400">{p.operation}</span>
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-sm font-mono text-emerald-400 font-semibold">
                  ${p.total_cost_usd.toFixed(4)}
                </span>
                <span className="text-xs font-mono text-amber-300">
                  {p.total_credits_deducted.toFixed(1)} credits
                </span>
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                {p.total_requests} requests · {p.total_units} units
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Usage Logs Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
            Recent Metered Deductions Audit Log
          </h3>
          <select
            value={filterProvider}
            onChange={(e) => setFilterProvider(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 rounded px-2.5 py-1 focus:outline-none"
          >
            <option value="all">All Providers</option>
            <option value="groq">Groq</option>
            <option value="brightdata">Bright Data</option>
            <option value="scrapegraph">ScrapeGraphAI</option>
            <option value="admin_grant">Admin Grants</option>
          </select>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Organization / User</th>
                <th className="py-3 px-4">Provider</th>
                <th className="py-3 px-4">Operation</th>
                <th className="py-3 px-4">Units</th>
                <th className="py-3 px-4">Cost (USD)</th>
                <th className="py-3 px-4 text-right">Credits</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-500">
                    Loading usage log...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-500">
                    No usage logs recorded yet.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-sans font-medium text-slate-200">{log.org_name || log.org_id}</div>
                      {log.user_email && <div className="text-slate-500 text-[11px]">{log.user_email}</div>}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                        {getProviderIcon(log.provider)}
                        {log.provider}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{log.operation}</td>
                    <td className="py-3 px-4 text-slate-400">{log.units}</td>
                    <td className="py-3 px-4 text-emerald-400">${log.cost_usd.toFixed(4)}</td>
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

export default UsagePage
