import React, { useState, useEffect } from "react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"
import { Skeleton } from "@/components/ui/States"
import { adminService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"
import { adminAuditLabel, adminMessage, formatAdminDateTime, formatAdminRelative } from "@/i18n/adminMessages"
import {
  ScrollText,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const PROVIDERS = [
  "adyntel",
  "meta_graph",
  "apify",
  "metapi",
  "groq",
  "gemini_media",
  "gemini",
  "scrapegraph",
  "system",
]

const OPERATIONS = [
  "discover_search",
  "ai_insight",
  "pattern_synthesis",
  "image_generate",
  "video_generate",
  "credit_grant",
  "plan_switch",
]

function finiteNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

function formatNumber(value, lang, minimumFractionDigits = 0, maximumFractionDigits = 2) {
  return new Intl.NumberFormat(lang === "ar" ? "ar" : "en", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(finiteNumber(value))
}

function formatCurrency(value, lang) {
  return new Intl.NumberFormat(lang === "ar" ? "ar" : "en", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(finiteNumber(value))
}

export function AuditLogPage() {
  const { lang, isRtl } = useLanguage()
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const [providerFilter, setProviderFilter] = useState("")
  const [operationFilter, setOperationFilter] = useState("")
  const [userFilter, setUserFilter] = useState("")
  const [selectedLog, setSelectedLog] = useState(null)

  const fetchLogs = async (targetPage = 1) => {
    setLoading(true)
    setError(false)
    try {
      const params = { page: targetPage, page_size: 30 }
      if (providerFilter) params.provider = providerFilter
      if (operationFilter) params.operation = operationFilter
      if (userFilter) params.user_id = userFilter

      const res = await adminService.getUsageLogsFiltered(params)
      setLogs(Array.isArray(res?.items) ? res.items : [])
      setTotal(res?.total || 0)
      setPage(res?.page || targetPage)
      setHasMore(Boolean(res?.has_more))
    } catch {
      setError(true)
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(1)
  }, [providerFilter, operationFilter])

  const handleSearchSubmit = (event) => {
    event.preventDefault()
    fetchLogs(1)
  }

  const previousIcon = isRtl ? ChevronRight : ChevronLeft
  const nextIcon = isRtl ? ChevronLeft : ChevronRight
  const PreviousIcon = previousIcon
  const NextIcon = nextIcon
  const meta = loading
    ? adminMessage(lang, "Loading")
    : error
      ? adminMessage(lang, "Unavailable")
      : adminMessage(lang, "Live · {count} events", { count: formatNumber(total, lang) })

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="w-full flex-1 flex flex-col font-sans">
      <BreadcrumbBar
        trail={["Console", "System", "Audit Log"].map((segment) => adminMessage(lang, segment))}
        meta={meta}
        actions={
          <Button size="xs" variant="ghost" onClick={() => fetchLogs(page)} disabled={loading}>
            <RefreshCw className={`me-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            {adminMessage(lang, "Refresh")}
          </Button>
        }
      />

      <div className="p-4 md:p-6 w-full">
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-text flex items-center gap-2.5">
                <ScrollText className="w-5 h-5 text-accent" />
                {adminMessage(lang, "Audit Trail & Operation Logs")}
              </h1>
              <p className="text-xs text-text-muted mt-0.5">
                {adminMessage(lang, "Immutable, real-time audit log of user operations, provider calls, credit deductions, and system events.")}
              </p>
            </div>
            <span className="font-mono text-xs px-2.5 py-1 rounded bg-surface-2 border border-border text-text-muted">
              {adminMessage(lang, "Total events: {count}", { count: formatNumber(total, lang) })}
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-border bg-surface-2 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs text-text-muted">
                <Filter className="w-3.5 h-3.5 text-accent" aria-hidden="true" />
                <label htmlFor="audit-provider" className="font-mono text-[11px]">{adminMessage(lang, "Provider:")}</label>
              </div>
              <select
                id="audit-provider"
                aria-label={adminMessage(lang, "Provider")}
                value={providerFilter}
                onChange={(event) => setProviderFilter(event.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent"
              >
                <option value="">{adminMessage(lang, "All Providers")}</option>
                {PROVIDERS.map((provider) => <option key={provider} value={provider}>{adminAuditLabel(lang, provider, "provider")}</option>)}
              </select>

              <div className="flex items-center gap-1.5 text-xs text-text-muted ms-2">
                <label htmlFor="audit-operation" className="font-mono text-[11px]">{adminMessage(lang, "Operation:")}</label>
              </div>
              <select
                id="audit-operation"
                aria-label={adminMessage(lang, "Operation")}
                value={operationFilter}
                onChange={(event) => setOperationFilter(event.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent"
              >
                <option value="">{adminMessage(lang, "All Operations")}</option>
                {OPERATIONS.map((operation) => <option key={operation} value={operation}>{adminAuditLabel(lang, operation, "operation")}</option>)}
              </select>
            </div>

            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
              <input
                type="text"
                aria-label={adminMessage(lang, "Filter by User ID or organization ID")}
                placeholder={adminMessage(lang, "Filter by User ID or organization ID")}
                value={userFilter}
                onChange={(event) => setUserFilter(event.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent w-48"
              />
              <Button size="xs" variant="primary" type="submit">{adminMessage(lang, "Apply")}</Button>
            </form>
          </div>

          <Panel className="flex min-w-0 flex-col overflow-hidden border border-border">
            <PanelHeader>
              <PanelTitle>{adminMessage(lang, "Event Log Stream")}</PanelTitle>
              <Tag className="" tone="default">
                {adminMessage(lang, "Page {page} · {count} entries", { page: formatNumber(page, lang), count: formatNumber(logs.length, lang) })}
              </Tag>
            </PanelHeader>

            {loading ? (
              <div className="p-6 space-y-3" role="status" aria-label={adminMessage(lang, "Loading")}>
                {Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-9 w-full rounded" />)}
              </div>
            ) : error ? (
              <div role="alert" className="m-4 rounded-lg border border-danger/30 bg-danger/5 p-5 text-start">
                <h2 className="text-sm font-semibold text-text">{adminMessage(lang, "Unable to load audit events.")}</h2>
                <p className="mt-1 text-xs text-text-muted">{adminMessage(lang, "Try adjusting the filters and retrying.")}</p>
                <Button className="mt-3" size="sm" variant="primary" onClick={() => fetchLogs(page)}>{adminMessage(lang, "Retry")}</Button>
              </div>
            ) : logs.length === 0 ? (
              <div className="py-16 text-center text-text-muted">
                <ScrollText className="w-8 h-8 text-text-faint mx-auto mb-2 opacity-50" aria-hidden="true" />
                <p className="text-sm font-semibold">{adminMessage(lang, "No audit events match filters")}</p>
                <p className="text-xs text-text-faint mt-1">{adminMessage(lang, "Try resetting the provider or operation criteria.")}</p>
              </div>
            ) : (
              <div className="min-w-0 overflow-auto">
                <table className="w-full min-w-[760px] table-fixed border-collapse text-start text-xs">
                  <thead className="sticky top-0 z-10 bg-surface-2 border-b border-border">
                    <tr>
                      <th scope="col" className="label-mono w-[110px] px-4 py-2.5 font-normal">{adminMessage(lang, "Event ID")}</th>
                      <th scope="col" className="label-mono w-[130px] px-3 py-2.5 font-normal">{adminMessage(lang, "Operation")}</th>
                      <th scope="col" className="label-mono w-[110px] px-3 py-2.5 font-normal">{adminMessage(lang, "Provider")}</th>
                      <th scope="col" className="label-mono px-3 py-2.5 font-normal">{adminMessage(lang, "User / Org")}</th>
                      <th scope="col" className="label-mono w-[85px] px-3 py-2.5 text-end font-normal">{adminMessage(lang, "Credits")}</th>
                      <th scope="col" className="label-mono w-[90px] px-3 py-2.5 text-end font-normal">{adminMessage(lang, "Est. Cost")}</th>
                      <th scope="col" className="label-mono w-[100px] px-4 py-2.5 text-end font-normal">{adminMessage(lang, "Timestamp")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {logs.map((log) => {
                      const operation = adminAuditLabel(lang, log.operation, "operation")
                      const provider = adminAuditLabel(lang, log.provider || "system", "provider")
                      const credits = formatNumber(log.credits_deducted, lang, 1, 1)
                      const cost = formatCurrency(log.cost_usd, lang)
                      return (
                        <tr key={log.id} onClick={() => setSelectedLog(log)} className="hover:bg-surface-2/40 transition cursor-pointer">
                          <td className="px-4 py-3 font-mono text-[11px] text-text-muted" dir="auto">{log.id ? String(log.id).slice(0, 8) : "—"}</td>
                          <td className="px-3 py-3"><span className="font-mono font-medium text-text text-[11px] px-1.5 py-0.5 rounded bg-surface-2 border border-border">{operation}</span></td>
                          <td className="px-3 py-3"><span className="font-mono text-accent text-[11px]">{provider}</span></td>
                          <td className="px-3 py-3 font-mono text-[11px] text-text-muted truncate" dir="auto">{log.user_email || log.user_id || log.org_id || adminMessage(lang, "System")}</td>
                          <td className="px-3 py-3 text-end font-mono text-[11px] text-amber-400">{adminMessage(lang, "Credits: {amount}", { amount: credits })}</td>
                          <td className="px-3 py-3 text-end font-mono text-[11px] text-text-muted">{adminMessage(lang, "Estimated cost: {amount}", { amount: cost })}</td>
                          <td className="px-4 py-3 text-end font-mono text-[11px] text-text-faint whitespace-nowrap">{formatAdminRelative(log.created_at, lang)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="p-3 border-t border-border flex items-center justify-between bg-surface-2/60">
              <span className="text-xs font-mono text-text-muted">
                {adminMessage(lang, "Showing page {page} of {pages}", { page: formatNumber(page, lang), pages: formatNumber(Math.max(1, Math.ceil(total / 30)), lang) })}
              </span>
              <div className="flex items-center gap-2">
                <Button size="xs" variant="ghost" disabled={page <= 1 || loading} onClick={() => fetchLogs(page - 1)}>
                  <PreviousIcon className="me-1 w-3.5 h-3.5" />{adminMessage(lang, "Previous")}
                </Button>
                <Button size="xs" variant="ghost" disabled={!hasMore || loading} onClick={() => fetchLogs(page + 1)}>
                  {adminMessage(lang, "Next")}<NextIcon className="ms-1 w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setSelectedLog(null) }}>
          <div role="dialog" aria-modal="true" aria-labelledby="audit-event-title" className="w-full max-w-md rounded-xl border border-border bg-surface-2 p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-border pb-3">
              <div>
                <h3 id="audit-event-title" className="text-base font-bold text-text">{adminMessage(lang, "Audit Event Inspector")}</h3>
                <span className="font-mono text-xs text-text-faint">{selectedLog.id}</span>
              </div>
              <button type="button" aria-label={adminMessage(lang, "Close")} onClick={() => setSelectedLog(null)} className="text-text-muted hover:text-text p-1 rounded">✕</button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">{adminMessage(lang, "Operation")}</span>
                <span className="font-mono font-semibold text-text">{adminAuditLabel(lang, selectedLog.operation, "operation")}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">{adminMessage(lang, "Provider")}</span>
                <span className="font-mono text-accent">{adminAuditLabel(lang, selectedLog.provider || "system", "provider")}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">{adminMessage(lang, "User Email / ID")}</span>
                <span className="font-mono text-text" dir="auto">{selectedLog.user_email || selectedLog.user_id || adminMessage(lang, "N/A")}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">{adminMessage(lang, "Credits Deducted")}</span>
                <span className="font-mono text-amber-400">{formatNumber(selectedLog.credits_deducted, lang, 1, 1)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">{adminMessage(lang, "Timestamp")}</span>
                <span className="font-mono text-text-muted" dir="auto">{formatAdminDateTime(selectedLog.created_at, lang)}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="xs" variant="primary" onClick={() => setSelectedLog(null)}>{adminMessage(lang, "Close")}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AuditLogPage
