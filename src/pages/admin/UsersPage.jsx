import React, { useState, useEffect } from "react"
import { adminService } from "@/services"
import { 
  Users, 
  UserCheck, 
  ShieldAlert, 
  ExternalLink, 
  Search, 
  RefreshCw, 
  CheckCircle2, 
  Key,
  Ban,
  Shield,
  Activity,
  X,
  CreditCard
} from "lucide-react"
import { Link } from "react-router-dom"

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [impersonatingId, setImpersonatingId] = useState(null)

  // Plan switch modal
  const [planSwitchUser, setPlanSwitchUser] = useState(null)
  const [selectedPlanId, setSelectedPlanId] = useState("")

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const [usersData, plansData] = await Promise.all([
        adminService.listUsers(),
        adminService.listPlans()
      ])
      setUsers(Array.isArray(usersData) ? usersData : [])
      setPlans(Array.isArray(plansData) ? plansData : [])
    } catch (err) {
      setError(err.message || "Failed to load users")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const handleBanToggle = async (user) => {
    const action = user.is_banned ? "unban" : "ban"
    if (!confirm(`Are you sure you want to ${action} ${user.email}? ${action === "ban" ? "This will block login completely." : ""}`)) {
      return
    }
    try {
      await adminService.banUser(user.id, !user.is_banned)
      showToast(`User ${user.email} ${user.is_banned ? "unbanned" : "banned"} successfully.`)
      fetchUsers()
    } catch (err) {
      alert(err.message || "Failed to update ban status")
    }
  }

  const handleRoleChange = async (user, newRole) => {
    try {
      await adminService.updateUserRole(user.id, newRole)
      showToast(`User ${user.email} role changed to ${newRole}.`)
      fetchUsers()
    } catch (err) {
      alert(err.message || "Failed to update user role")
    }
  }

  const handleSwitchPlan = async (e) => {
    e.preventDefault()
    if (!planSwitchUser || !selectedPlanId) return

    try {
      await adminService.switchUserPlan(planSwitchUser.id, selectedPlanId)
      showToast(`Switched plan for ${planSwitchUser.email} successfully.`)
      setPlanSwitchUser(null)
      fetchUsers()
    } catch (err) {
      alert(err.message || "Failed to switch plan")
    }
  }

  const handleImpersonate = async (user) => {
    if (!confirm(`Are you sure you want to impersonate ${user.email}? You will be logged in as this user.`)) {
      return
    }
    setImpersonatingId(user.id)
    try {
      const res = await adminService.impersonateUser(user.id)
      if (res?.access_token) {
        localStorage.setItem("helix_auth_token", res.access_token)
        showToast(`Impersonating ${user.email}... Redirecting to Discovery.`)
        setTimeout(() => {
          window.location.href = "/discover"
        }, 1200)
      }
    } catch (err) {
      alert(err.message || "Failed to impersonate user")
    } finally {
      setImpersonatingId(null)
    }
  }

  const filteredUsers = users.filter((u) =>
    u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.full_name && u.full_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (u.organization_name && u.organization_name.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Users className="w-7 h-7 text-indigo-400" />
            User Management & Impersonation
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage user roles, ban abusive accounts, override plans, and view filtered usage logs.
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Filter */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
        <input
          type="text"
          placeholder="Search by name, email, or organization..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Users Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-mono">
                <th className="py-3.5 px-4 font-semibold">User</th>
                <th className="py-3.5 px-4 font-semibold">Role</th>
                <th className="py-3.5 px-4 font-semibold">Organization / Plan</th>
                <th className="py-3.5 px-4 font-semibold">Status</th>
                <th className="py-3.5 px-4 font-semibold">Created</th>
                <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 font-mono">
                    Loading users...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 font-mono">
                    No users found matching search.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-200">{u.full_name || u.email.split("@")[0]}</div>
                      <div className="font-mono text-slate-400 text-[11px]">{u.email}</div>
                    </td>

                    <td className="py-3.5 px-4">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u, e.target.value)}
                        className={`px-2 py-1 rounded text-[11px] font-mono uppercase bg-slate-950 border focus:outline-none ${
                          u.role === "admin"
                            ? "border-rose-500/40 text-rose-400"
                            : u.role === "assistant-admin"
                            ? "border-amber-500/40 text-amber-400"
                            : "border-slate-800 text-slate-300"
                        }`}
                      >
                        <option value="customer">customer</option>
                        <option value="assistant-admin">assistant-admin</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="text-slate-300 font-medium">{u.organization_name || "—"}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[11px] text-teal-400 font-mono">{u.plan_name || "Custom"}</span>
                        <button
                          onClick={() => {
                            setPlanSwitchUser(u)
                            setSelectedPlanId(u.plan_id || "")
                          }}
                          className="text-[10px] text-slate-500 hover:text-slate-300 underline"
                        >
                          Change
                        </button>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                        u.is_banned
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                          : u.is_suspended
                          ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      }`}>
                        {u.status}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>

                    <td className="py-3.5 px-4 text-right space-x-2">
                      {/* Ban / Unban Button */}
                      <button
                        onClick={() => handleBanToggle(u)}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                          u.is_banned
                            ? "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30"
                            : "bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {u.is_banned ? "Unban" : "Ban"}
                      </button>

                      {/* Impersonate */}
                      <button
                        onClick={() => handleImpersonate(u)}
                        disabled={impersonatingId === u.id || u.is_banned}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded border border-slate-700 transition inline-flex items-center gap-1"
                      >
                        <Key className="w-3 h-3 text-amber-400" />
                        {impersonatingId === u.id ? "Logging in..." : "Impersonate"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Plan Override Modal */}
      {planSwitchUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-teal-400" /> Switch Workspace Plan
              </h2>
              <button onClick={() => setPlanSwitchUser(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Select a new subscription tier for <span className="text-slate-200 font-semibold">{planSwitchUser.email}</span>.
            </p>

            <form onSubmit={handleSwitchPlan} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Target Plan</label>
                <select
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-teal-500"
                >
                  <option value="">Select Plan...</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.credit_allowance} credits • ${p.price_monthly || 0}/mo)
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPlanSwitchUser(null)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedPlanId}
                  className="px-5 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition"
                >
                  Update Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default UsersPage
