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
  ShieldCheck,
  Edit2
} from "lucide-react"

export function SubscriptionsPlansPage() {
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

  // Edit plan modal
  const [editingPlan, setEditingPlan] = useState(null)
  const [editName, setEditName] = useState("")
  const [editAllowance, setEditAllowance] = useState(100)
  const [editPriceMonthly, setEditPriceMonthly] = useState(0.0)
  const [editDailyImages, setEditDailyImages] = useState(5)
  const [editDailyVideos, setEditDailyVideos] = useState(3)
  const [editFlags, setEditFlags] = useState({})
  const [isUpdating, setIsUpdating] = useState(false)

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

  const handleOpenEdit = (plan) => {
    setEditingPlan(plan)
    setEditName(plan.name)
    setEditAllowance(plan.credit_allowance)
    setEditPriceMonthly(plan.price_monthly || 0.0)
    setEditDailyImages(plan.daily_image_limit || 5)
    setEditDailyVideos(plan.daily_video_limit || 3)
    setEditFlags({ ...(plan.feature_flags || {}) })
  }

  const handleSaveEdit = async (e) => {
    e.preventDefault()
    if (!editingPlan) return

    setIsUpdating(true)
    try {
      await adminService.updatePlan(editingPlan.id, {
        name: editName,
        credit_allowance: parseInt(editAllowance, 10),
        price_monthly: parseFloat(editPriceMonthly),
        daily_image_limit: parseInt(editDailyImages, 10),
        daily_video_limit: parseInt(editDailyVideos, 10),
        feature_flags: editFlags
      })
      showToast(`Plan "${editName}" updated successfully! Changes take effect immediately.`)
      setEditingPlan(null)
      fetchPlans()
    } catch (err) {
      alert(err.message || "Failed to update plan")
    } finally {
      setIsUpdating(false)
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
            Configure system plans, trial allowances, daily image/video limits, and toggle feature flags.
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
              className={`p-6 rounded-2xl border flex flex-col justify-between transition ${
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
                  <button
                    onClick={() => handleOpenEdit(p)}
                    className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition"
                  >
                    <Edit2 className="w-3 h-3 text-indigo-400" /> Edit
                  </button>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-slate-100">{p.name}</h3>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-2xl font-mono font-bold text-slate-200">
                      ${p.price_monthly || 0}
                    </span>
                    <span className="text-xs text-slate-400">/ month</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    <span className="font-semibold text-teal-400">{p.credit_allowance}</span> credits • Daily: {p.daily_image_limit || 5} img / {p.daily_video_limit || 3} vid
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
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

      {/* Edit Plan Modal */}
      {editingPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-indigo-400" /> Edit Plan: {editingPlan.name}
              </h2>
              <button
                onClick={() => setEditingPlan(null)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Plan Name</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Monthly Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editPriceMonthly}
                    onChange={(e) => setEditPriceMonthly(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Credit Allowance</label>
                  <input
                    type="number"
                    value={editAllowance}
                    onChange={(e) => setEditAllowance(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Daily Images Limit</label>
                  <input
                    type="number"
                    value={editDailyImages}
                    onChange={(e) => setEditDailyImages(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Daily Videos Limit</label>
                  <input
                    type="number"
                    value={editDailyVideos}
                    onChange={(e) => setEditDailyVideos(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">Feature Flags</label>
                <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded-xl border border-slate-800">
                  {ALL_FEATURES.map((feat) => {
                    const isChecked = editFlags[feat.key] !== false
                    return (
                      <label key={feat.key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => setEditFlags({ ...editFlags, [feat.key]: e.target.checked })}
                          className="rounded border-slate-700 bg-slate-800 text-indigo-500 focus:ring-0"
                        />
                        {feat.label}
                      </label>
                    )
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingPlan(null)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition"
                >
                  {isUpdating ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white">Create Custom Plan</h2>
              <button onClick={() => setShowCreateModal(false)} className="p-1 rounded text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreatePlan} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Plan Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Enterprise Tier"
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Credit Allowance</label>
                  <input
                    type="number"
                    value={creditAllowance}
                    onChange={(e) => setCreditAllowance(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Price Per Credit ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={pricePerCredit}
                    onChange={(e) => setPricePerCredit(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">Feature Flags</label>
                <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded-xl border border-slate-800">
                  {ALL_FEATURES.map((feat) => (
                    <label key={feat.key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={flags[feat.key]}
                        onChange={(e) => setFlags({ ...flags, [feat.key]: e.target.checked })}
                        className="rounded border-slate-700 bg-slate-800 text-indigo-500 focus:ring-0"
                      />
                      {feat.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition"
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

export default SubscriptionsPlansPage
