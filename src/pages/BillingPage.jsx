import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"
import { useWorkspaceAccess } from "@/hooks/useWorkspaceAccess"
import { Button } from "@/components/ui/Button"
import { useAuth } from "@/context/AuthContext"
import { useW8Copy } from "@/i18n/w8Product"
import { SupportMailto } from "@/components/SupportMailto"
import { PlansSection } from "@/features/plans/PlansSection"
import { usePricingCopy } from "@/i18n/pricing"

const FEATURES = [
  { flag: "discover", copy: "featureDiscover" },
  { flag: "monitors", copy: "featureMonitors" },
  { flag: "swipe_files", copy: "featureBoards" },
]

/** Stored Metapi record counts from /account/usage/today; nothing when absent. */
export function RecordsMeter({ usage, w8 }) {
  const used = usage?.records_used_this_month
  const cap = usage?.records_cap_this_month
  if (typeof used !== "number" || typeof cap !== "number") return null
  const pct = cap > 0 ? Math.min(100, Math.round((used / cap) * 100)) : 100
  return (
    <div className="space-y-1.5 pt-2" data-testid="records-meter">
      <p className="font-medium">{w8.recordsMeterTitle}</p>
      <div className="h-2 w-full overflow-hidden rounded-sm bg-bg" role="progressbar" aria-valuemin={0} aria-valuemax={cap} aria-valuenow={used} aria-label={w8.recordsMeterTitle}>
        <div className={pct >= 100 ? "h-full bg-danger" : "h-full bg-accent"} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-text-muted">{w8.recordsMeterBody(used, cap)}</p>
      {usage.platform_records_paused ? <p role="alert" className="text-danger">{w8.recordsPlatformPaused}</p>
        : used >= cap ? <p role="alert" className="text-danger">{w8.recordsMeterFull}</p> : null}
    </div>
  )
}

export function BillingPage() {
  const { t } = useLanguage()
  const w8 = useW8Copy()
  const { user, refreshSession } = useAuth()
  const planCopy = usePricingCopy()
  const [params] = useSearchParams()
  const highlightId = params.get("plan") || undefined
  const returnedFromPayment = params.get("billing") === "returned"
  const flags = user?.feature_flags ?? {}
  const { access, usage, loading, error, submitting, refresh, requestAccess } = useWorkspaceAccess()
  const [note, setNote] = useState("")
  const [requestError, setRequestError] = useState(false)
  const [sent, setSent] = useState(false)
  const status = access?.status

  // Back from the payment page. The server grants access only when it receives
  // the payment confirmation, which can land after the user is back, so the page
  // refreshes the access state for up to a minute. Nothing here grants anything:
  // a paid plan shows up when the server says so (its grant is not the trial's).
  const [activation, setActivation] = useState(returnedFromPayment ? "waiting" : null)
  const attempts = useRef(0)
  const paid = status === "approved" && Boolean(access?.plan_id) && !String(access.plan_id).startsWith("plan_trial")
  useEffect(() => {
    if (!returnedFromPayment || activation !== "waiting") return undefined
    if (paid) {
      setActivation("done")
      refreshSession?.()
      return undefined
    }
    if (attempts.current >= 15) {
      setActivation("slow")
      return undefined
    }
    const timer = setTimeout(() => { attempts.current += 1; refresh() }, 4000)
    return () => clearTimeout(timer)
  }, [returnedFromPayment, activation, paid, refresh, refreshSession])
  const statusKeys = { approved: "accessApproved", pending: "accessPending", rejected: "accessRejected", expired: "accessExpired", revoked: "accessRevoked" }

  async function submit(event) {
    event.preventDefault()
    setRequestError(false)
    setSent(false)
    try { await requestAccess(note); setSent(true) }
    catch { setRequestError(true) }
  }

  return (
    <section className="mx-auto w-full max-w-3xl space-y-6 p-6 sm:p-8">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-text">{t("accessUsage")}</h1>
        <Button onClick={refresh} disabled={loading}>{t("refresh")}</Button>
      </div>
      <p className="text-sm leading-relaxed text-text-muted">{w8.accessIntro}</p>
      <p className="text-sm text-text-muted">{w8.accessSupport} <SupportMailto /></p>
      {loading ? <p role="status">{t("loading")}</p> : error ? <p role="alert" className="text-danger">{t("requestFailed")}</p> : (
        <>
          <p className="border border-border bg-surface p-4" role="status">{t("accessStatusLabel")}: {statusKeys[status] ? t(statusKeys[status]) : t("unknownValue")}</p>
          {activation ? (
            <p role="status" className="border border-border bg-surface p-4 text-sm">
              {activation === "done" ? planCopy.activated : activation === "slow" ? planCopy.activationSlow : planCopy.activating}
            </p>
          ) : null}
          <PlansSection access={access} highlightId={highlightId} />
          {status !== "approved" && (
            <form onSubmit={submit} className="space-y-3 border border-border bg-surface p-4">
              <h2 className="font-semibold">{t("requestAccessTitle")}</h2>
              <label className="block space-y-2 text-sm"><span>{t("requestNoteLabel")}</span><textarea value={note} maxLength={2000} onChange={(event) => setNote(event.target.value)} className="block min-h-24 w-full rounded-sm border border-border bg-bg p-2" /></label>
              <Button type="submit" variant="primary" disabled={submitting}>{t(submitting ? "sendingRequest" : "submitAccessRequest")}</Button>
              {requestError && <p role="alert" className="text-sm text-danger">{t("requestFailed")}</p>}
              {sent && <p role="status" className="text-sm">{t("accessRequestSent")}</p>}
            </form>
          )}
          <div className="space-y-2 border border-border bg-surface p-4 text-sm">
            <h2 className="font-semibold">{w8.accessFeaturesTitle}</h2>
            <ul className="space-y-1.5">
              {FEATURES.map(({ flag, copy }) => (
                <li key={flag} className="flex items-baseline gap-3">
                  <span className={flags[flag] === true ? "label-mono w-14 shrink-0 text-success" : "label-mono w-14 shrink-0 text-text-faint"}>
                    {flags[flag] === true ? w8.accessGranted : w8.accessNotGranted}
                  </span>
                  <span className="text-text-muted">{w8[copy]}</span>
                </li>
              ))}
            </ul>
          </div>
          {status !== "approved" && (
            <div className="space-y-1 border border-border bg-surface p-4 text-sm">
              <h2 className="font-semibold">{w8.accessNextTitle}</h2>
              <p className="text-text-muted">{w8.accessNextBody}</p>
            </div>
          )}
          <div className="space-y-2 border border-border bg-surface p-4 text-sm">
            <h2 className="font-semibold">{t("recordedUsage")}</h2>
            <p>{t("searchesLabel")}: {typeof usage?.searches_run_today === "number" ? usage.searches_run_today : t("unknownValue")}</p>
            <RecordsMeter usage={usage} w8={w8} />
            <p>{t("usageDisclosure")}</p>
          </div>
        </>
      )}
    </section>
  )
}

export default BillingPage
