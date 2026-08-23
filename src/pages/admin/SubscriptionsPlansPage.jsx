import React, { useState, useEffect } from "react"
import { adminService } from "@/services"
import { 
  CreditCard, 
  PlusCircle, 
  Check, 
  X, 
  Sparkles, 
  RefreshCw, 
  CheckCircle2, 
  ShieldCheck 
} from "lucide-react"

export default function SubscriptionsPlansPage() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  // Create plan modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [name, setName] = useState("")
  const [creditAllowance, setCreditAllowance] = useState(100)
  const [pricePerCredit, setPricePerCredit] = useState(0.01)
  const [flags, setFlags] = useState({
    discover: true,
    intelligence: true,
    create: true,
    performance: true,
    swipe_files: true,
    team_accounts: true,
    public_api: false,
  })
  const [submitting, setSubmitting] = useState(false)

  const fetchPlans = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminService.listPlans()
      setPlans(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || "Failed to load plans")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPlans()
  }, [])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const handleCreatePlan = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await adminService.createPlan({
        name,
        type: "custom",
        credit_allowance: parseInt(creditAllowance, 10),
        price_per_credit: parseFloat(pricePerCredit),
        feature_flags: flags,
      })
      showToast(`Custom plan "${name}" created successfully!`)
      setShowCreateModal(false)
      setName("")
      setCreditAllowance(100)
      fetchPlans()
    } catch (err) {
      alert(err.message || "Failed to create plan")
    } finally {
      setSubmitting(false)
    }
  }

  const ALL_FEATURES = [
    { key: "discover", label: "Discover Search" },
    { key: "intelligence", label: "Brand Intelligence" },
    { key: "create", label: "Creative Generation" },
    { key: "performance", label: "Performance Analytics" },
    { key: "swipe_files", label: "Swipe Files & Boards" },
    { key: "team_accounts", label: "Team Accounts" },
    { key: "public_api", label: "Public API Access" },
  ]

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <CreditCard className="w-7 h-7 text-indigo-400" />
            Plans & Subscriptions Management
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Configure system plans, trial allowances, and custom feature tiers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPlans}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded shadow-lg shadow-indigo-600/20 transition"
          >
            <PlusCircle className="w-4 h-4" />
            Create Custom Plan
          </button>
        </div>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Plan Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-3 py-12 text-center text-slate-500 font-mono text-xs">
            Loading plans...
          </div>
        ) : (
          plans.map((p) => (
            <div
              key={p.id}
              className={`p-6 rounded-xl border flex flex-col justify-between transition ${
                p.type === "trial"
                  ? "bg-slate-900/60 border-slate-800"
                  : p.type === "pay_as_you_go"
                  ? "bg-slate-900/90 border-indigo-500/30 shadow-lg shadow-indigo-950/40"
                  : "bg-slate-900/60 border-amber-500/30"
              }`}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase tracking-wider ${
                    p.type === "trial"
                      ? "bg-slate-800 text-slate-300"
                      : p.type === "pay_as_you_go"
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                      : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                  }`}>
                    {p.type}
                  </span>
                  {p.price_per_credit ? (
                    <span className="font-mono text-xs text-slate-400">
                      ${p.price_per_credit.toFixed(3)} / credit
                    </span>
                  ) : (
                    <span className="font-mono text-xs text-emerald-400">Free Tier</span>
                  )}
                </div>

                <div>
                  <h3 className="text-lg font-bold text-slate-100">{p.name}</h3>
                  <div className="text-2xl font-mono font-bold text-slate-200 mt-2">
                    {p.credit_allowance} <span className="text-xs text-slate-400 font-normal">Credits allowance</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                    Feature Access
                  </div>
                  {ALL_FEATURES.map((feat) => {
                    const active = p.feature_flags && p.feature_flags[feat.key] !== false
                    return (
                      <div key={feat.key} className="flex items-center justify-between text-xs py-0.5">
                        <span className={active ? "text-slate-300" : "text-slate-500"}>
                          {feat.label}
                        </span>
                        {active ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <X className="w-3.5 h-3.5 text-slate-600" />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] font-mono text-slate-500">
                Plan ID: {p.id}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Custom Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              Create Custom Organization Plan
            </h3>
            <form onSubmit={handleCreatePlan} className="space-y-4">
              <div>
                <label className="text-xs font-mono text-slate-400">Plan Name</label>
                <input
                  type="text"
                  placeholder="e.g. VIP Brand Agency Tier"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-mono text-slate-400">Credit Allowance</label>
                  <input
                    type="number"
                    value={creditAllowance}
                    onChange={(e) => setCreditAllowance(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-mono text-slate-400">Price Per Credit ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={pricePerCredit}
                    onChange={(e) => setPricePerCredit(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1.5">
                  Unlocked Feature Flags
                </label>
                <div className="space-y-1.5 max-h-44 overflow-y-auto">
                  {ALL_FEATURES.map((feat) => (
                    <label key={feat.key} className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800 hover:border-slate-700 cursor-pointer">
                      <span className="text-xs text-slate-300 font-sans">{feat.label}</span>
                      <input
                        type="checkbox"
                        checked={flags[feat.key]}
                        onChange={(e) => setFlags({ ...flags, [feat.key]: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-700 text-indigo-500 w-4 h-4"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded transition"
                >
                  {submitting ? "Creating..." : "Create Plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
