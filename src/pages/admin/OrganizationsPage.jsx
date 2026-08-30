import React, { useState, useEffect } from "react"
import { adminService } from "@/services"
import { 
  Building2, 
  Coins, 
  Layers, 
  Sliders, 
  CheckCircle2, 
  AlertTriangle, 
  Search, 
  RefreshCw,
  PlusCircle,
  ShieldAlert
} from "lucide-react"

export function OrganizationsPage() {
  const [orgs, setOrgs] = useState([])
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  // Modals state
  const [grantModalOrg, setGrantModalOrg] = useState(null)
  const [grantAmount, setGrantAmount] = useState(50)
  const [grantReason, setGrantReason] = useState("Admin manual grant")
  const [submittingGrant, setSubmittingGrant] = useState(false)

  const [switchModalOrg, setSwitchModalOrg] = useState(null)
  const [selectedPlanId, setSelectedPlanId] = useState("")
  const [resetCredits, setResetCredits] = useState(false)
  const [submittingSwitch, setSubmittingSwitch] = useState(false)

  const [flagsModalOrg, setFlagsModalOrg] = useState(null)
  const [currentFlags, setCurrentFlags] = useState({})
  const [submittingFlags, setSubmittingFlags] = useState(false)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [orgsData, plansData] = await Promise.all([
        adminService.listOrganizations(),
        adminService.listPlans(),
      ])
      setOrgs(Array.isArray(orgsData) ? orgsData : [])
      setPlans(Array.isArray(plansData) ? plansData : [])
    } catch (err) {
      setError(err.message || "Failed to load organizations")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const handleGrantCredits = async (e) => {
    e.preventDefault()
    if (!grantModalOrg) return
    setSubmittingGrant(true)
    try {
      const res = await adminService.grantCredits(grantModalOrg.id, parseFloat(grantAmount), grantReason)
      showToast(res.message || `Granted ${grantAmount} credits successfully`)
      setGrantModalOrg(null)
      fetchAll()
    } catch (err) {
      alert(err.message || "Failed to grant credits")
    } finally {
      setSubmittingGrant(false)
    }
  }

  const handleSwitchPlan = async (e) => {
    e.preventDefault()
    if (!switchModalOrg || !selectedPlanId) return
    setSubmittingSwitch(true)
    try {
      const res = await adminService.switchPlan(switchModalOrg.id, selectedPlanId, resetCredits)
      showToast(res.message || "Plan updated successfully")
      setSwitchModalOrg(null)
      fetchAll()
    } catch (err) {
      alert(err.message || "Failed to switch plan")
    } finally {
      setSubmittingSwitch(false)
    }
  }

  const handleUpdateFlags = async (e) => {
    e.preventDefault()
    if (!flagsModalOrg) return
    setSubmittingFlags(true)
    try {
      const res = await adminService.updateFeatureFlags(flagsModalOrg.id, currentFlags)
      showToast(res.message || "Feature flags updated successfully")
      setFlagsModalOrg(null)
      fetchAll()
    } catch (err) {
      alert(err.message || "Failed to update flags")
    } finally {
      setSubmittingFlags(false)
    }
  }

  const filteredOrgs = orgs.filter((o) =>
    o.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.owner_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.plan_name.toLowerCase().includes(searchTerm.toLowerCase())
  )

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
            <Building2 className="w-7 h-7 text-indigo-400" />
            Organizations & Quota Control
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage organization plans, credit balances, quota limits, and custom feature flags.
          </p>
        </div>
        <button
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <Search className="w-4 h-4 text-slate-500 ml-2" />
        <input
          type="text"
          placeholder="Filter by organization name, owner email, or plan..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-transparent text-slate-200 placeholder-slate-500 text-sm focus:outline-none w-full"
        />
      </div>

      {/* Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
            <tr>
              <th className="py-3.5 px-4">Organization / Owner</th>
              <th className="py-3.5 px-4">Active Plan</th>
              <th className="py-3.5 px-4">Credit Balance</th>
              <th className="py-3.5 px-4">Credits Used</th>
              <th className="py-3.5 px-4">Status</th>
              <th className="py-3.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
            {loading ? (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-500">
                  Loading organizations...
                </td>
              </tr>
            ) : filteredOrgs.length === 0 ? (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-500">
                  No organizations found.
                </td>
              </tr>
            ) : (
              filteredOrgs.map((org) => (
                <tr key={org.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-sans font-semibold text-slate-200 text-sm">{org.name}</div>
                    <div className="text-slate-400 text-xs">{org.owner_email}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs">
                      {org.plan_name}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-1.5 text-amber-300 font-bold">
                      <Coins className="w-3.5 h-3.5 text-amber-400" />
                      {org.credit_balance.toFixed(1)} cr
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {org.credits_used.toFixed(1)} cr
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] ${
                      org.status === "active"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : org.status === "trial_expired"
                        ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      {org.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2">
                    <button
                      onClick={() => {
                        setGrantModalOrg(org)
                        setGrantAmount(50)
                        setGrantReason("Admin manual grant")
                      }}
                      className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded transition text-xs"
                    >
                      + Grant
                    </button>
                    <button
                      onClick={() => {
                        setSwitchModalOrg(org)
                        setSelectedPlanId(org.plan_id)
                        setResetCredits(false)
                      }}
                      className="px-2.5 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded transition text-xs"
                    >
                      Plan
                    </button>
                    <button
                      onClick={() => {
                        setFlagsModalOrg(org)
                        setCurrentFlags({ ...org.effective_feature_flags })
                      }}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded transition text-xs"
                    >
                      Flags
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Grant Credits Modal */}
      {grantModalOrg && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Coins className="w-5 h-5 text-amber-400" />
              Grant Custom Credits
            </h3>
            <p className="text-xs text-slate-400">
              Grant credits to <strong className="text-slate-200">{grantModalOrg.name}</strong> (Current balance: {grantModalOrg.credit_balance.toFixed(1)} credits).
            </p>
            <form onSubmit={handleGrantCredits} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400">Credit Amount</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={grantAmount}
                  onChange={(e) => setGrantAmount(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-amber-400"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-mono text-slate-400">Reason / Reference</label>
                <input
                  type="text"
                  value={grantReason}
                  onChange={(e) => setGrantReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-amber-400"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setGrantModalOrg(null)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingGrant}
                  className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded transition"
                >
                  {submittingGrant ? "Granting..." : "Confirm Grant"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Switch Plan Modal */}
      {switchModalOrg && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              Switch Organization Plan
            </h3>
            <p className="text-xs text-slate-400">
              Assign a new active plan to <strong className="text-slate-200">{switchModalOrg.name}</strong>.
            </p>
            <form onSubmit={handleSwitchPlan} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400">Select Plan</label>
                <select
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                  required
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.type} — {p.credit_allowance} allowance)
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="resetCredits"
                  checked={resetCredits}
                  onChange={(e) => setResetCredits(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-700 text-indigo-500"
                />
                <label htmlFor="resetCredits" className="text-xs text-slate-300">
                  Reset credit balance to plan's default allowance
                </label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSwitchModalOrg(null)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingSwitch}
                  className="px-4 py-1.5 bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold text-xs rounded transition"
                >
                  {submittingSwitch ? "Updating..." : "Update Plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Feature Flags Modal */}
      {flagsModalOrg && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-400" />
              Custom Feature Flags: {flagsModalOrg.name}
            </h3>
            <p className="text-xs text-slate-400">
              Toggle specific features for this organization. Enabled features unlock product surfaces immediately.
            </p>
            <form onSubmit={handleUpdateFlags} className="space-y-3">
              <div className="space-y-2 py-2">
                {ALL_FEATURES.map((feat) => (
                  <label key={feat.key} className="flex items-center justify-between p-2.5 rounded bg-slate-950/60 border border-slate-800 hover:border-slate-700 cursor-pointer">
                    <span className="text-xs text-slate-200 font-sans">{feat.label}</span>
                    <input
                      type="checkbox"
                      checked={currentFlags[feat.key] ?? true}
                      onChange={(e) => setCurrentFlags({ ...currentFlags, [feat.key]: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-700 text-indigo-500 w-4 h-4"
                    />
                  </label>
                ))}
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setFlagsModalOrg(null)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingFlags}
                  className="px-4 py-1.5 bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold text-xs rounded transition"
                >
                  {submittingFlags ? "Saving..." : "Save Feature Flags"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default OrganizationsPage
