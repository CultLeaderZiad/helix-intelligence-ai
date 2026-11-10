import { useState } from "react"
import { KeyRound } from "lucide-react"
import { adminService } from "@/services"
import { adminMessage } from "@/i18n/adminMessages"

/** Features an admin can grant (backend GRANTABLE_FEATURES). */
export const ACCESS_FEATURES = [
  { key: "discover", label: "Discover Search" },
  { key: "swipe_files", label: "Swipe Files & Boards" },
  { key: "monitors", label: "Monitors" },
]

const DAY_MS = 24 * 60 * 60 * 1000

/** yyyy-mm-dd for a date input. */
export function toDateInput(date) {
  return date ? new Date(date).toISOString().slice(0, 10) : ""
}

/**
 * The new end date when extending by `days`: counted from the current end
 * date if it is still in the future, otherwise from now.
 */
export function extendFrom(currentEnd, days, now = Date.now()) {
  const end = currentEnd ? new Date(currentEnd).getTime() : 0
  return new Date(Math.max(end, now) + days * DAY_MS)
}

/** Whole days left until `end` (0 when past). */
export function daysLeft(end, now = Date.now()) {
  if (!end) return null
  return Math.max(0, Math.ceil((new Date(end).getTime() - now) / DAY_MS))
}

/**
 * Admin dialog: set which features a workspace may use and until when, or
 * revoke access. Saving creates a new grant (the server keeps the history);
 * revoking stops access and deletes no data.
 */
export function ManageAccessDialog({ org, lang, onClose, onSaved }) {
  const t = (msg, values) => adminMessage(lang, msg, values)
  const approved = org.access_status === "approved"
  const [features, setFeatures] = useState(() =>
    Object.fromEntries(
      ACCESS_FEATURES.map((f) => [f.key, approved ? org.access_features?.[f.key] === true : true]),
    ),
  )
  const [endDate, setEndDate] = useState(() =>
    toDateInput(approved && org.access_expires_at ? org.access_expires_at : extendFrom(null, 7)),
  )
  const [noEnd, setNoEnd] = useState(approved && !org.access_expires_at)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const extend = (days) => {
    setNoEnd(false)
    setEndDate(toDateInput(extendFrom(approved ? org.access_expires_at : null, days)))
  }

  async function save(e) {
    e.preventDefault()
    if (!Object.values(features).some(Boolean)) {
      setError(t("Choose at least one feature, or revoke access instead."))
      return
    }
    setBusy(true)
    setError(null)
    try {
      await adminService.grantOrganizationAccess(org.id, {
        plan_id: org.plan_id,
        feature_flags: features,
        // End of the chosen day, UTC.
        expires_at: noEnd ? null : `${endDate}T23:59:59Z`,
      })
      onSaved(t("Access updated for {name}.", { name: org.name }))
    } catch (err) {
      console.error("Failed to update access", err)
      setError(t("Could not update access."))
    } finally {
      setBusy(false)
    }
  }

  async function revoke() {
    setBusy(true)
    setError(null)
    try {
      await adminService.revokeOrganizationAccess(org.id, "Revoked from Organizations")
      onSaved(t("Access revoked for {name}. Their data is kept.", { name: org.name }))
    } catch (err) {
      console.error("Failed to revoke access", err)
      setError(t("Could not revoke access."))
    } finally {
      setBusy(false)
    }
  }

  const left = approved ? daysLeft(org.access_expires_at) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="manage-access-title"
        className="w-full max-w-lg space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <h3 id="manage-access-title" className="flex items-center gap-2 text-lg font-bold text-slate-100">
          <KeyRound className="h-5 w-5 text-emerald-400" aria-hidden="true" />
          {t("Manage access: {name}", { name: org.name })}
        </h3>
        <p className="text-xs text-slate-400">
          {approved
            ? org.access_expires_at
              ? t("Access ends {date} ({days} days left).", { date: toDateInput(org.access_expires_at), days: left })
              : t("Access has no end date.")
            : t("This workspace has no access right now.")}
        </p>
        {error ? (
          <div role="alert" className="rounded border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
            {error}
          </div>
        ) : null}
        <form onSubmit={save} className="space-y-4">
          <fieldset className="space-y-2">
            <legend className="mb-1 font-mono text-xs text-slate-400">{t("Features")}</legend>
            {ACCESS_FEATURES.map((f) => (
              <label
                key={f.key}
                className="flex cursor-pointer items-center justify-between rounded border border-slate-800 bg-slate-950/60 p-2.5 hover:border-slate-700"
              >
                <span className="font-sans text-xs text-slate-200">{t(f.label)}</span>
                <input
                  type="checkbox"
                  checked={features[f.key]}
                  onChange={(e) => setFeatures({ ...features, [f.key]: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900"
                />
              </label>
            ))}
          </fieldset>

          <div className="space-y-2">
            <label htmlFor="access-end" className="font-mono text-xs text-slate-400">
              {t("Access ends")}
            </label>
            <input
              id="access-end"
              type="date"
              value={endDate}
              disabled={noEnd}
              min={toDateInput(new Date())}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:opacity-50"
              required={!noEnd}
            />
            <div className="flex flex-wrap gap-2">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => extend(d)}
                  className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-700"
                >
                  {t("+{days} days", { days: d })}
                </button>
              ))}
              <label className="flex items-center gap-1.5 text-xs text-slate-300">
                <input type="checkbox" checked={noEnd} onChange={(e) => setNoEnd(e.target.checked)} />
                {t("No end date")}
              </label>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2">
            {approved ? (
              <button
                type="button"
                onClick={revoke}
                disabled={busy}
                className="rounded border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/20"
              >
                {t("Revoke access")}
              </button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
              >
                {t("Cancel")}
              </button>
              <button
                type="submit"
                disabled={busy}
                className="rounded bg-emerald-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
              >
                {busy ? t("Saving...") : t("Save access")}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
