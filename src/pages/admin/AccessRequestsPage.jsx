import React, { useEffect, useState } from "react"
import { adminService } from "@/services"
import { ShieldCheck, RefreshCw } from "lucide-react"

const FEATURES = [
  "discover",
  "intelligence",
  "create",
  "performance",
  "swipe_files",
  "team_accounts",
  "public_api",
  "scout",
  "leadgen",
  "monitors",
]

export function AccessRequestsPage() {
  const [requests, setRequests] = useState([])
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [planId, setPlanId] = useState("")
  const [expiry, setExpiry] = useState("")
  const [flags, setFlags] = useState(() => Object.fromEntries(FEATURES.map((key) => [key, false])))
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
      const list = Array.isArray(planRows) ? planRows : []
      setPlans(list)
      if (!planId && list[0]?.id) setPlanId(list[0].id)
    } catch (err) {
      setError(err?.message || "Access requests could not be loaded")
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
    } catch (err) {
      setError(err?.message || "Approval failed")
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
      setRevokeState(result?.status || "revoked")
      await load()
    } catch (err) {
      setError(err?.message || "Revoke failed")
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
    } catch (err) {
      setError(err?.message || "Rejection failed")
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            Access requests
          </h1>
          <p dir="auto" className="text-sm text-slate-400 mt-1">
            Approve a workspace by choosing a plan, the features to turn on, and an optional expiry. Rejection and revocation keep the workspace data.
          </p>
        </div>
        <button type="button" onClick={load} className="text-xs font-mono text-slate-300 border border-slate-700 rounded px-3 py-1.5">
          <RefreshCw className={`w-3.5 h-3.5 inline ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {error && <p className="text-sm text-rose-300">{error}</p>}

      <div className="border border-slate-800 rounded-xl p-4 space-y-3 bg-slate-900/60">
        <label className="block text-xs text-slate-400">
          Plan
          <select value={planId} onChange={(event) => setPlanId(event.target.value)} className="mt-1 w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-100">
            {plans.length === 0 && <option value="">No plans loaded</option>}
            {plans.map((plan) => (
              <option key={plan.id} value={plan.id}>{plan.name} ({plan.id})</option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Expiry (optional)
          <input type="datetime-local" value={expiry} onChange={(event) => setExpiry(event.target.value)} className="mt-1 w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-100" />
        </label>
        <div className="flex flex-wrap gap-3">
          {FEATURES.map((key) => (
            <label key={key} className="text-xs text-slate-300 flex items-center gap-1.5">
              <input type="checkbox" checked={Boolean(flags[key])} onChange={() => toggle(key)} />
              {key}
            </label>
          ))}
        </div>
      </div>

      <div className="border border-slate-800 rounded-xl p-4 space-y-2 bg-slate-900/60">
        <label className="block text-xs text-slate-400">
          Revoke workspace access
          <input value={revokeOrgId} onChange={(event) => setRevokeOrgId(event.target.value)} placeholder="Workspace id" className="mt-1 w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-100 font-mono" />
        </label>
        <button type="button" disabled={!revokeOrgId || busyId === revokeOrgId} onClick={revoke} className="text-xs px-3 py-1.5 rounded border border-rose-800 text-rose-200 disabled:opacity-50">Revoke access</button>
        {revokeState && <p className="text-xs text-slate-300">Revoke status: {revokeState}. Workspace data is kept.</p>}
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading requests…</p>
      ) : requests.length === 0 ? (
        <p dir="auto" className="text-sm text-slate-400">No pending access requests.</p>
      ) : (
        <ul className="space-y-3">
          {requests.map((row) => (
            <li key={row.id} className="border border-slate-800 rounded-xl p-4 bg-slate-900/40">
              <p className="text-sm text-slate-100">Workspace {row.org_id}</p>
              <p className="text-xs text-slate-400 mt-1">Requested: {(row.requested_features || []).join(", ") || "—"}</p>
              {row.note && <p className="text-xs text-slate-500 mt-1">{row.note}</p>}
              <div className="flex gap-2 mt-3">
                <button type="button" disabled={busyId === row.id || !planId} onClick={() => approve(row.id)} className="text-xs px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50">Approve</button>
                <button type="button" disabled={busyId === row.id} onClick={() => reject(row.id)} className="text-xs px-3 py-1.5 rounded border border-slate-600 text-slate-200">Reject</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default AccessRequestsPage
