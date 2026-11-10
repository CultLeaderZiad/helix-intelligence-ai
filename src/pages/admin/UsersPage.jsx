import React, { useState, useEffect } from "react"
import { adminService, authService } from "@/services"
import { Users, Search, RefreshCw, CheckCircle2, Key } from "lucide-react"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { useLanguage } from "@/context/LanguageContext"
import {
  adminAccessLabel,
  adminAccountStatusLabel,
  adminMessage,
  adminRoleLabel,
  formatAdminDate,
  getAdminAccessStatus,
} from "@/i18n/adminMessages"

export function UsersPage() {
  const { lang, isRtl, t } = useLanguage()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [impersonatingId, setImpersonatingId] = useState(null)
  const [banTargetUser, setBanTargetUser] = useState(null)
  const [isBanModalBusy, setIsBanModalBusy] = useState(false)
  const [impersonateTargetUser, setImpersonateTargetUser] = useState(null)

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const usersData = await adminService.listUsers()
      setUsers(Array.isArray(usersData) ? usersData : [])
    } catch (err) {
      console.error("Failed to load users", err)
      setError(adminMessage(lang, "Failed to load users."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
    const interval = setInterval(() => {
      adminService.listUsers().then((usersData) => {
        if (Array.isArray(usersData)) setUsers(usersData)
      }).catch((err) => console.error("Failed to refresh users", err))
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const showToast = (message) => {
    setToast(message)
    setTimeout(() => setToast(null), 4000)
  }

  const confirmBanToggle = async () => {
    if (!banTargetUser) return
    setIsBanModalBusy(true)
    setError(null)
    try {
      await adminService.banUser(banTargetUser.id, !banTargetUser.is_banned)
      showToast(adminMessage(lang, "User {email} {action} successfully.", {
        email: banTargetUser.email,
        action: banTargetUser.is_banned ? "unbanned" : "banned",
      }))
      setBanTargetUser(null)
      await fetchUsers()
    } catch (err) {
      console.error("Failed to update ban status", err)
      setError(adminMessage(lang, "Failed to update ban status."))
    } finally {
      setIsBanModalBusy(false)
    }
  }

  const handleRoleChange = async (user, newRole) => {
    setError(null)
    try {
      await adminService.updateUserRole(user.id, newRole)
      showToast(adminMessage(lang, "User {email} role changed to {role}.", {
        email: user.email,
        role: adminRoleLabel(lang, newRole),
      }))
      await fetchUsers()
    } catch (err) {
      console.error("Failed to update user role", err)
      setError(adminMessage(lang, "Failed to update user role."))
    }
  }

  const confirmImpersonate = async () => {
    if (!impersonateTargetUser) return
    setError(null)
    setImpersonatingId(impersonateTargetUser.id)
    try {
      const res = await adminService.impersonateUser(impersonateTargetUser.id)
      if (res?.access_token) {
        authService.switchToImpersonatedSession(res.access_token)
        showToast(t("impersonationProgress").replace("{email}", impersonateTargetUser.email))
        window.location.replace("/discover")
      } else {
        setError(t("impersonationFailed"))
      }
    } catch (err) {
      console.error("Failed to impersonate user", err)
      setError(t("impersonationFailed"))
    } finally {
      setImpersonatingId(null)
      setImpersonateTargetUser(null)
    }
  }

  const filteredUsers = users.filter((user) =>
    (user.email || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.full_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.organization_name || "").toLowerCase().includes(searchTerm.toLowerCase())
  )
  const approvedCount = users.filter((user) => getAdminAccessStatus(user) === "approved").length
  const adminCount = users.filter((user) => user.role === "admin").length

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="w-full max-w-7xl mx-auto p-6 md:p-8 space-y-8 font-sans">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Users className="w-7 h-7 text-indigo-400" />
            {adminMessage(lang, "User Management & Impersonation")}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {adminMessage(lang, "Manage user roles, ban abusive accounts, and review admin-granted workspace access.")}
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          {adminMessage(lang, "Refresh")}
        </button>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}
      {error && (
        <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchUsers} className="underline text-xs font-mono ms-4">{adminMessage(lang, "Retry")}</button>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Summary label={adminMessage(lang, "Total Users")} value={users.length} />
        <Summary label={adminMessage(lang, "Approved access")} value={approvedCount} tone="text-emerald-400" />
        <Summary label={adminMessage(lang, "Administrators")} value={adminCount} tone="text-indigo-400" />
        <Summary label={adminMessage(lang, "Active Filtered")} value={filteredUsers.length} tone="text-accent" />
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute start-3 top-3 text-slate-500" />
        <input
          type="text"
          placeholder={adminMessage(lang, "Search by name, email, or organization...")}
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          className="w-full ps-9 pe-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-indigo-500"
        />
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-start border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-mono">
                <th className="py-3.5 px-4 font-semibold">{adminMessage(lang, "User Email")}</th>
                <th className="py-3.5 px-4 font-semibold">{adminMessage(lang, "Role")}</th>
                <th className="py-3.5 px-4 font-semibold">{adminMessage(lang, "Organization / Access")}</th>
                <th className="py-3.5 px-4 font-semibold">{adminMessage(lang, "Account status")}</th>
                <th className="py-3.5 px-4 font-semibold">{adminMessage(lang, "Created")}</th>
                <th className="py-3.5 px-4 font-semibold text-end">{adminMessage(lang, "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr><td colSpan={6} className="py-12 text-center text-slate-500 font-mono">{adminMessage(lang, "Loading users...")}</td></tr>
              ) : filteredUsers.length === 0 ? (
                <tr><td colSpan={6} className="py-12 text-center text-slate-500 font-mono">{adminMessage(lang, "No users found matching search.")}</td></tr>
              ) : filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-slate-800/30 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-slate-200">{user.full_name || user.email.split("@")[0]}</div>
                    <div className="font-mono text-slate-400 text-[11px]">{user.email}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    <select
                      value={user.role}
                      onChange={(event) => handleRoleChange(user, event.target.value)}
                      className="px-2 py-1 rounded text-[11px] font-mono uppercase bg-slate-950 border border-slate-800 text-slate-300 focus:outline-none"
                      aria-label={adminMessage(lang, "Role")}
                    >
                      <option value="customer">{adminRoleLabel(lang, "customer")}</option>
                      <option value="assistant-admin">{adminRoleLabel(lang, "assistant-admin")}</option>
                      <option value="admin">{adminRoleLabel(lang, "admin")}</option>
                    </select>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="text-slate-300 font-medium">{user.organization_name || adminMessage(lang, "None")}</div>
                    <div className="text-[11px] text-emerald-300 font-mono">
                      {adminAccessLabel(lang, getAdminAccessStatus(user), Boolean(user.organization_id))}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                      user.is_banned
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                        : user.is_suspended
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                        : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    }`}>
                      {adminAccountStatusLabel(lang, user.status)}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                    {formatAdminDate(user.created_at, lang)}
                  </td>
                  <td className="py-3.5 px-4 text-end space-x-2">
                    <button
                      onClick={() => setBanTargetUser(user)}
                      className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                        user.is_banned
                          ? "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      {adminMessage(lang, user.is_banned ? "Unban" : "Ban")}
                    </button>
                    <button
                      onClick={() => setImpersonateTargetUser(user)}
                      disabled={impersonatingId === user.id || user.is_banned}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded border border-slate-700 transition inline-flex items-center gap-1"
                    >
                      <Key className="w-3 h-3 text-amber-400" />
                      {adminMessage(lang, impersonatingId === user.id ? "Logging in..." : "Impersonate")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!banTargetUser}
        title={adminMessage(lang, banTargetUser?.is_banned ? "Unban User Account" : "Ban User Account")}
        description={banTargetUser?.is_banned
          ? adminMessage(lang, "Are you sure you want to unban {email}? Their account access and login capabilities will be immediately restored.", { email: banTargetUser?.email ?? "" })
          : adminMessage(lang, "Are you sure you want to ban {email}? This will immediately invalidate their sessions and block all login attempts.", { email: banTargetUser?.email ?? "" })}
        confirmText={adminMessage(lang, banTargetUser?.is_banned ? "Unban Account" : "Ban Account")}
        cancelText={adminMessage(lang, "Cancel")}
        variant={banTargetUser?.is_banned ? "primary" : "danger"}
        isBusy={isBanModalBusy}
        onConfirm={confirmBanToggle}
        onCancel={() => setBanTargetUser(null)}
      />
      <ConfirmDialog
        isOpen={!!impersonateTargetUser}
        title={t("impersonationTitle")}
        description={t("impersonationDescription").replace("{email}", impersonateTargetUser?.email ?? "")}
        confirmText={t("impersonationConfirm")}
        cancelText={t("cancel")}
        variant="warning"
        isBusy={impersonatingId === impersonateTargetUser?.id}
        onConfirm={confirmImpersonate}
        onCancel={() => setImpersonateTargetUser(null)}
      />
    </div>
  )
}

function Summary({ label, value, tone = "text-slate-100" }) {
  return (
    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
      <span className="text-[11px] font-mono text-slate-400 block">{label}</span>
      <span className={`text-xl font-bold font-mono ${tone}`}>{value}</span>
    </div>
  )
}

export default UsersPage
