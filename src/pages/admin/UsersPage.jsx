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
  Key 
} from "lucide-react"

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [impersonatingId, setImpersonatingId] = useState(null)

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminService.listUsers()
      setUsers(Array.isArray(data) ? data : [])
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
    (u.organization_name && u.organization_name.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Users className="w-7 h-7 text-indigo-400" />
            User Directory & Support Impersonation
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            View customer accounts, trial statuses, and impersonate sessions for live support.
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
      <div className="flex items-center gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <Search className="w-4 h-4 text-slate-500 ml-2" />
        <input
          type="text"
          placeholder="Filter by email or organization..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-transparent text-slate-200 placeholder-slate-500 text-sm focus:outline-none w-full"
        />
      </div>

      {/* Users Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
            <tr>
              <th className="py-3.5 px-4">User / Email</th>
              <th className="py-3.5 px-4">Role</th>
              <th className="py-3.5 px-4">Organization</th>
              <th className="py-3.5 px-4">Trial Expiry</th>
              <th className="py-3.5 px-4">Registered</th>
              <th className="py-3.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
            {loading ? (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-500">
                  Loading users...
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-500">
                  No users found.
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-sans font-semibold text-slate-200 text-sm">{user.email}</div>
                    <div className="text-slate-500 text-[11px]">ID: {user.id}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono ${
                      user.role === "admin"
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                        : "bg-slate-800 text-slate-300"
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-sans text-slate-300">
                    {user.organization_name || "—"}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {user.trial_expires_at ? new Date(user.trial_expires_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleImpersonate(user)}
                      disabled={impersonatingId === user.id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded transition text-xs font-sans font-medium"
                    >
                      <Key className="w-3 h-3" />
                      {impersonatingId === user.id ? "Connecting..." : "Impersonate"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default UsersPage
