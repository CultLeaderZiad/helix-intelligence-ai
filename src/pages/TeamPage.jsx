import React, { useState, useEffect } from "react"
import { accountService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { 
  Users, 
  UserPlus, 
  Mail, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  ShieldCheck, 
  Copy,
  AlertCircle,
} from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"

export function TeamPage() {
  const { user } = useAuth()
  const [team, setTeam] = useState(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [cancelInviteTarget, setCancelInviteTarget] = useState(null)
  const [removeMemberTarget, setRemoveMemberTarget] = useState(null)
  const [isActionBusy, setIsActionBusy] = useState(false)

  // Invite modal
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [email, setEmail] = useState("")
  const [role, setRole] = useState("member")
  const [submitting, setSubmitting] = useState(false)
  const [inviteError, setInviteError] = useState(null)

  const isFeatureEnabled = user?.feature_flags?.team_accounts === true

  const fetchTeam = async () => {
    if (!isFeatureEnabled) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const data = await accountService.getTeam()
      setTeam(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTeam()
  }, [isFeatureEnabled])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const handleInvite = async (e) => {
    e.preventDefault()
    setInviteError(null)
    setSubmitting(true)
    try {
      const res = await accountService.inviteTeamMember(email, role)
      showToast(res.message || `Invitation created for ${email}`)
      setShowInviteModal(false)
      setEmail("")
      fetchTeam()
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || "Failed to send invitation"
      setInviteError(typeof detail === "string" ? detail : "Failed to send invitation")
    } finally {
      setSubmitting(false)
    }
  }

  const confirmCancelInvite = async () => {
    if (!cancelInviteTarget) return
    setIsActionBusy(true)
    try {
      await accountService.cancelTeamInvite(cancelInviteTarget.id)
      showToast(`Invitation for ${cancelInviteTarget.email} canceled`)
      setCancelInviteTarget(null)
      fetchTeam()
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || "Failed to cancel invitation"
      showToast(typeof detail === "string" ? detail : "Failed to cancel invitation")
    } finally {
      setIsActionBusy(false)
    }
  }

  const confirmRemoveMember = async () => {
    if (!removeMemberTarget) return
    setIsActionBusy(true)
    try {
      await accountService.removeTeamMember(removeMemberTarget.id)
      showToast(`Member ${removeMemberTarget.email} removed from team`)
      setRemoveMemberTarget(null)
      fetchTeam()
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || "Failed to remove team member"
      showToast(typeof detail === "string" ? detail : "Failed to remove team member")
    } finally {
      setIsActionBusy(false)
    }
  }

  const copyInviteLink = (token) => {
    const link = `${window.location.origin}/sign-up?invite=${token}`
    navigator.clipboard.writeText(link)
    showToast("Invite link copied to clipboard!")
  }

  if (!isFeatureEnabled) {
    return (
      <div className="p-12 max-w-4xl mx-auto text-center space-y-4 font-sans">
        <Users className="w-12 h-12 text-slate-600 mx-auto" />
        <h2 className="text-xl font-bold text-slate-200">Team Accounts Locked</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Your current organization plan is limited to a single user seat. Upgrade your plan or enable the Team Accounts feature flag to invite colleagues.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 font-sans">
      <BreadcrumbBar trail={["Helix", "Settings", "Team Members"]} />
      <div className="w-full max-w-7xl mx-auto p-6 md:p-8 space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Users className="w-7 h-7 text-indigo-400" />
            Team Members & Multi-Seat Management
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage your workspace members. All team members share your organization's plan and credit pool.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchTeam}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-accent hover:bg-accent-dim text-black text-xs font-semibold rounded border border-accent hover:border-accent-dim transition"
          >
            <UserPlus className="w-4 h-4" />
            Invite Teammate
          </button>
        </div>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* Active Members Table */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
          Active Workspace Members
        </h3>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Member Email</th>
                <th className="py-3.5 px-4">Role</th>
                <th className="py-3.5 px-4">Joined At</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {loading ? (
                <tr>
                  <td colSpan="4" className="py-8 text-center text-slate-500">
                    Loading team...
                  </td>
                </tr>
              ) : (team?.members || []).map((m) => (
                <tr key={m.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4 font-sans font-semibold text-slate-200">{m.email}</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase ${
                      m.role === "owner"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                    }`}>
                      {m.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "Founding Member"}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    {m.role !== "owner" && (
                      <button
                        onClick={() => setRemoveMemberTarget(m)}
                        title="Remove team member"
                        className="text-slate-500 hover:text-rose-400 p-1 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Invites Table */}
      {(team?.invites || []).length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
            Pending Email Invitations
          </h3>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Invitee Email</th>
                  <th className="py-3.5 px-4">Assigned Role</th>
                  <th className="py-3.5 px-4">Expires</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {team.invites.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-sans text-slate-200">{inv.email}</td>
                    <td className="py-3.5 px-4 text-indigo-300">{inv.role}</td>
                    <td className="py-3.5 px-4 text-slate-400">{new Date(inv.expires_at).toLocaleDateString()}</td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => copyInviteLink(inv.token)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition"
                      >
                        Copy Link
                      </button>
                      <button
                        onClick={() => setCancelInviteTarget(inv)}
                        className="text-rose-400 hover:text-rose-300 p-1 transition"
                        title="Cancel invitation"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-indigo-400" />
              Invite Team Member
            </h3>
            {inviteError && (
              <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {inviteError}
              </div>
            )}
            <form onSubmit={handleInvite} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400">Email Address</label>
                <input
                  type="email"
                  placeholder="colleague@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-mono text-slate-400">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                >
                  <option value="member">Member (Can search and analyze)</option>
                  <option value="admin">Admin (Can manage billing & invites)</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-accent hover:bg-accent-dim text-black font-semibold text-xs rounded border border-accent hover:border-accent-dim transition"
                >
                  {submitting ? "Sending..." : "Send Invitation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation modal for cancelling invitation */}
      <ConfirmDialog
        isOpen={Boolean(cancelInviteTarget)}
        title="Cancel Team Invitation"
        description={`Are you sure you want to cancel the pending invite for ${cancelInviteTarget?.email}? The invitation link will immediately expire.`}
        confirmText="Cancel Invitation"
        variant="danger"
        isBusy={isActionBusy}
        onConfirm={confirmCancelInvite}
        onCancel={() => setCancelInviteTarget(null)}
      />

      {/* Confirmation modal for removing team member */}
      <ConfirmDialog
        isOpen={Boolean(removeMemberTarget)}
        title="Remove Team Member"
        description={`Are you sure you want to remove ${removeMemberTarget?.email} from the workspace team? They will immediately lose access to team workspaces, monitors, swipe files, and shared credit pools.`}
        confirmText="Remove Member"
        variant="danger"
        isBusy={isActionBusy}
        onConfirm={confirmRemoveMember}
        onCancel={() => setRemoveMemberTarget(null)}
      />

      </div>
    </div>
  )
}

export default TeamPage
