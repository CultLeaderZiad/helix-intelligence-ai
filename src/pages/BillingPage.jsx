import { useState } from "react"
import { useLanguage } from "@/context/LanguageContext"
import { useWorkspaceAccess } from "@/hooks/useWorkspaceAccess"
import { Button } from "@/components/ui/Button"

export function BillingPage() {
  const { t } = useLanguage()
  const { access, usage, loading, error, submitting, refresh, requestAccess } = useWorkspaceAccess()
  const [note, setNote] = useState("")
  const [requestError, setRequestError] = useState(false)
  const [sent, setSent] = useState(false)
  const status = access?.status
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
      <p className="text-sm leading-relaxed text-text-muted">{t("accessDescription")}</p>
      {loading ? <p role="status">{t("loading")}</p> : error ? <p role="alert" className="text-danger">{t("requestFailed")}</p> : (
        <>
          <p className="border border-border bg-surface p-4" role="status">{t("accessStatusLabel")}: {statusKeys[status] ? t(statusKeys[status]) : t("unknownValue")}</p>
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
            <h2 className="font-semibold">{t("recordedUsage")}</h2>
            <p>{t("searchesLabel")}: {typeof usage?.searches_today === "number" ? usage.searches_today : t("unknownValue")}</p>
            <p>{t("usageDisclosure")}</p>
          </div>
        </>
      )}
    </section>
  )
}

export default BillingPage
