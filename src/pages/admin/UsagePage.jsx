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
  Search,
  Filter,
  User,
  Building
} from "lucide-react"

export function UsagePage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterProvider, setFilterProvider] = useState("all")
  const [searchTerm, setSearchTerm] = useState("")

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
  const filteredLogs = logs.filter((l) => {
    const matchesProvider = filterProvider === "all" || l.provider.toLowerCase() === filterProvider.toLowerCase()
    const matchesSearch = !searchTerm || 
      (l.user_email && l.user_email.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.org_name && l.org_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.operation && l.operation.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesProvider && matchesSearch
  })

  const getProviderIcon = (provider) => {
    switch (provider.toLowerCase()) {
      case "groq":
        return <Cpu className="w-4 h-4 text-emerald-400" />
      case "metapi":
        return <Globe className="w-4 h-4 text-teal-400" />
      case "scrapegraph":
        return <Sparkles className="w-4 h-4 text-amber-400" />
      case "gemini":
        return <Sparkles className="w-4 h-4 text-indigo-400" />
      default:
        return <Activity className="w-4 h-4 text-slate-400" />
    }
  }

  const formatLogTime = (val) => {
    if (!val) return "—"
    const cleaned = typeof val === "string" ? val.replace(/\+00:00Z$/, "Z").replace(/\+00:00$/, "Z") : val
    const d = new Date(cleaned)
    return isNaN(d.getTime()) ? "—" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Gauge className="w-7 h-7 text-indigo-400" />
            Global Usage & Per-User Metering
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real provider spend tracking and granular deduction audit across all users.
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
            ${Number(summary?.total_cost_usd || 0).toFixed(4)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Direct third-party API spend</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Credits Deducted</span>
            <Coins className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-indigo-400 mt-2">
            {Number(summary?.total_credits_deducted || 0).toFixed(1)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Platform user balance billed</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Total Operations</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-slate-200 mt-2">
            {summary?.total_requests || 0}
          </div>
          <p className="text-xs text-slate-500 mt-1">Total metered API events</p>
        </div>
      </div>

      {/* Search & Provider Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search by user email, org, or operation..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={filterProvider}
            onChange={(e) => setFilterProvider(e.target.value)}
            className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Providers</option>
            <option value="metapi">Metapi (Domain Trace)</option>
            <option value="groq">Groq (Pattern Engine)</option>
            <option value="scrapegraph">ScrapeGraphAI (Deep Read)</option>
            <option value="gemini">Gemini / Creative Media</option>
            <option value="helix_playbook">Helix Playbook</option>
            <option value="discover_composite">Discover Pipeline</option>
          </select>
        </div>
      </div>

      {/* Granular Logs Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Recent Metered Deductions ({filteredLogs.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/20 text-slate-400 font-mono">
                <th className="py-3 px-4 font-semibold">Time</th>
                <th className="py-3 px-4 font-semibold">User / Workspace</th>
                <th className="py-3 px-4 font-semibold">Provider</th>
                <th className="py-3 px-4 font-semibold">Operation</th>
                <th className="py-3 px-4 font-semibold text-right">Units</th>
                <th className="py-3 px-4 font-semibold text-right">Cost (USD)</th>
                <th className="py-3 px-4 font-semibold text-right">Credits Deducted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 font-mono">
                    Loading usage logs...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 font-mono">
                    No usage logs matching current filters.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30 transition font-mono">
                    <td className="py-3 px-4 text-slate-400">{formatLogTime(log.created_at)}</td>
                    <td className="py-3 px-4">
                      <div className="text-slate-200 font-sans font-medium">{log.user_email || "Anonymous"}</div>
                      <div className="text-[10px] text-slate-500">{log.org_name || log.org_id || "—"}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        {getProviderIcon(log.provider)}
                        <span>{log.provider}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{log.operation}</td>
                    <td className="py-3 px-4 text-right text-slate-400">{log.units}</td>
                    <td className="py-3 px-4 text-right text-emerald-400 font-semibold">${Number(log.cost_usd || 0).toFixed(4)}</td>
                    <td className="py-3 px-4 text-right text-indigo-400 font-bold">-{Number(log.credits_deducted || 0).toFixed(1)} cr</td>
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
