import React, { useEffect, useState } from "react"
import { adminService } from "@/services"
import { ShieldCheck, RefreshCw } from "lucide-react"
import { useLanguage } from "@/context/LanguageContext"
import { adminAccessLabel, adminMessage } from "@/i18n/adminMessages"

const FEATURES = [
  { key: "discover", label: "Discover Search" },
  { key: "intelligence", label: "Brand Intelligence" },
  { key: "create", label: "Creative Generation" },
  { key: "performance", label: "Performance Analytics" },
  { key: "swipe_files", label: "Swipe Files" },
  { key: "team_accounts", label: "Team Accounts" },
  { key: "public_api", label: "Public API" },
  { key: "scout", label: "Scout" },
  { key: "leadgen", label: "Lead Generation" },
  { key: "monitors", label: "Monitors" },
]

const FEATURE_LABELS = Object.fromEntries(FEATURES.map(({ key, label }) => [key, label]))

function featureLabel(lang, feature) {
  const value = String(feature || "")
  const label = FEATURE_LABELS[value] || value.replaceAll("_", " ")
  return adminMessage(lang, label)
}

export function AccessRequestsPage() {
  const { lang, isRtl } = useLanguage()
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [planId, setPlanId] = useState("")
  const [expiry, setExpiry] = useState("")
  const [flags, setFlags] = useState(() => Object.fromEntries(FEATURES.map(({ key }) => [key, false])))
  const [revokeOrgId, setRevokeOrgId] = useState("")
  const [revokeState, setRevokeState] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [rows, planRows] = await Promise.all([
        adminService.listAccessRequests("pending"),
        adminService.listPlans(),
      ])
      const listRows = Array.isArray(rows) ? rows : []
      setRequests(listRows)
      if (listRows[0]?.org_id) setRevokeOrgId((current) => current || listRows[0].org_id)

      const availablePlans = Array.isArray(planRows) ? planRows : []
      setPlanId((current) => (
        availablePlans.some((plan) => String(plan.id) === current)
          ? current
          : String(availablePlans[0]?.id ?? "")
      ))
    } catch {
      setError(adminMessage(lang, "Unable to load access requests."))
      setRequests([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const toggle = (key) => setFlags((current) => ({ ...current, [key]: !current[key] }))

  const approve = async (requestId) => {
    setBusyId(requestId)
    setError(null)
    try {
      await adminService.approveAccessRequest(requestId, {
        plan_id: planId,
        feature_flags: flags,
        expires_at: expiry ? new Date(expiry).toISOString() : null,
      })
      await load()
    } catch {
      setError(adminMessage(lang, "Unable to approve this access request."))
    } finally {
      setBusyId(null)
    }
  }

  const revoke = async () => {
    if (!revokeOrgId) return
    setBusyId(revokeOrgId)
    setError(null)
    setRevokeState(null)
    try {
      const result = await adminService.revokeOrganizationAccess(revokeOrgId, "Revoked from the access console")
      setRevokeState(typeof result?.status === "string" ? result.status : null)
      await load()
    } catch {
      setError(adminMessage(lang, "Unable to revoke organization access."))
    } finally {
      setBusyId(null)
    }
  }

  const reject = async (requestId) => {
    setBusyId(requestId)
    setError(null)
    try {
      await adminService.rejectAccessRequest(requestId, "Rejected by platform admin")
      await load()
    } catch {
      setError(adminMessage(lang, "Unable to reject this access request."))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="p-6 md:p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            {adminMessage(lang, "Access requests")}
          </h1>
          <p className="text-sm text-slate-400 mt-1">{adminMessage(lang, "Manage pending requests for administrator-granted feature access.")}</p>
        </div>
        <button type="button" onClick={load} disabled={loading} aria-label={adminMessage(lang, "Refresh")} className="text-xs font-mono text-slate-300 border border-slate-700 rounded px-3 py-1.5 disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 inline ${loading ? "animate-spin" : ""}`} /> {adminMessage(lang, "Refresh")}
        </button>
      </div>

      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}

      <section aria-labelledby="admin-feature-access-title" className="border border-slate-800 rounded-xl p-4 space-y-3 bg-slate-900/60">
        <div>
          <h2 id="admin-feature-access-title" className="text-sm font-semibold text-slate-100">{adminMessage(lang, "Admin-granted feature access")}</h2>
          <p className="text-xs text-slate-400 mt-1">{adminMessage(lang, "Access is granted only by an administrator.")}</p>
        </div>
        <label className="block text-xs text-slate-400">
          {adminMessage(lang, "Optional access expiry")}
          <input type="datetime-local" aria-label={adminMessage(lang, "Optional access expiry")} value={expiry} onChange={(event) => setExpiry(event.target.value)} className="mt-1 w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-100" />
        </label>
        <div className="flex flex-wrap gap-3">
          {FEATURES.map(({ key, label }) => (
            <label key={key} className="text-xs text-slate-300 flex items-center gap-1.5">
              <input type="checkbox" checked={Boolean(flags[key])} onChange={() => toggle(key)} />
              {adminMessage(lang, label)}
            </label>
          ))}
        </div>
        {!planId && !loading && <p role="status" className="text-xs text-amber-300">{adminMessage(lang, "Access approval is unavailable because access configuration is missing.")}</p>}
      </section>

      <section aria-labelledby="revoke-access-title" className="border border-slate-800 rounded-xl p-4 space-y-2 bg-slate-900/60">
        <label id="revoke-access-title" className="block text-xs text-slate-400">
          {adminMessage(lang, "Revoke organization access")}
          <input value={revokeOrgId} onChange={(event) => setRevokeOrgId(event.target.value)} placeholder={adminMessage(lang, "Workspace ID")} aria-label={adminMessage(lang, "Workspace ID")} dir="auto" className="mt-1 w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-100 font-mono" />
        </label>
        <button type="button" disabled={!revokeOrgId || busyId === revokeOrgId} onClick={revoke} className="text-xs px-3 py-1.5 rounded border border-rose-800 text-rose-200 disabled:opacity-50">
          {busyId === revokeOrgId ? adminMessage(lang, "Revoking…") : adminMessage(lang, "Revoke access")}
        </button>
        {revokeState && <p className="text-xs text-slate-300" role="status">{adminMessage(lang, "Revocation status: {status}", { status: adminAccessLabel(lang, revokeState) })}</p>}
      </section>

      {loading ? (
        <p className="text-sm text-slate-400" role="status">{adminMessage(lang, "Loading access requests…")}</p>
      ) : requests.length === 0 ? (
        <p className="text-sm text-slate-400">{adminMessage(lang, "No pending access requests.")}</p>
      ) : (
        <ul className="space-y-3">
          {requests.map((row) => (
            <li key={row.id} className="border border-slate-800 rounded-xl p-4 bg-slate-900/40">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm text-slate-100" dir="auto">{adminMessage(lang, "Workspace ID")}: {row.org_id}</p>
                <span className="rounded border border-amber-800 px-2 py-0.5 text-xs text-amber-200">{adminAccessLabel(lang, "pending")}</span>
              </div>
              <p className="text-xs text-slate-400 mt-1" dir="auto">{adminMessage(lang, "Requested features")}: {(row.requested_features || []).map((feature) => featureLabel(lang, feature)).join(", ") || "—"}</p>
              {row.note && <p className="text-xs text-slate-500 mt-1" dir="auto">{row.note}</p>}
              <div className="flex gap-2 mt-3">
                <button type="button" disabled={busyId === row.id || !planId} onClick={() => approve(row.id)} className="text-xs px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50">
                  {busyId === row.id ? adminMessage(lang, "Approving…") : adminMessage(lang, "Approve access")}
                </button>
                <button type="button" disabled={busyId === row.id} onClick={() => reject(row.id)} className="text-xs px-3 py-1.5 rounded border border-slate-600 text-slate-200 disabled:opacity-50">
                  {busyId === row.id ? adminMessage(lang, "Rejecting…") : adminMessage(lang, "Reject request")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default AccessRequestsPage
