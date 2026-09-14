import React, { useState, useEffect } from "react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"
import { ErrorState, Skeleton } from "@/components/ui/States"
import { adminService } from "@/services"
import { formatRelative } from "@/lib/format"
import { 
  ScrollText, 
  Search, 
  RefreshCw, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  Shield,
  Activity,
  User,
  Clock,
  Coins
} from "lucide-react"

export function AuditLogPage() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters
  const [providerFilter, setProviderFilter] = useState("")
  const [operationFilter, setOperationFilter] = useState("")
  const [userFilter, setUserFilter] = useState("")
  const [selectedLog, setSelectedLog] = useState(null)

  const fetchLogs = async (targetPage = 1) => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        page: targetPage,
        page_size: 30,
      }
      if (providerFilter) params.provider = providerFilter
      if (operationFilter) params.operation = operationFilter
      if (userFilter) params.user_id = userFilter

      const res = await adminService.getUsageLogsFiltered(params)
      setLogs(Array.isArray(res?.items) ? res.items : [])
      setTotal(res?.total || 0)
      setPage(res?.page || targetPage)
      setHasMore(Boolean(res?.has_more))
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(1)
  }, [providerFilter, operationFilter])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    fetchLogs(1)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col font-sans">
      <BreadcrumbBar
        trail={["Console", "System", "Audit Log"]}
        meta={loading ? "loading" : error ? "unavailable" : `live (${total} events)`}
        actions={
          <Button size="xs" variant="ghost" onClick={() => fetchLogs(page)} disabled={loading}>
            <RefreshCw className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      />

      <div className="min-h-0 flex-1 overflow-auto p-4 md:p-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-text flex items-center gap-2.5">
                <ScrollText className="w-5 h-5 text-accent" />
                Audit Trail & Operation Logs
              </h1>
              <p className="text-xs text-text-muted mt-0.5">
                Immutable, real-time audit log of user operations, provider calls, credit deductions, and system events.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2.5 py-1 rounded bg-surface-2 border border-border text-text-muted">
                Total Events: {total}
              </span>
            </div>
          </div>

          {/* Filters Bar */}
          <div className="p-3.5 rounded-xl border border-border bg-surface-2 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs text-text-muted">
                <Filter className="w-3.5 h-3.5 text-accent" />
                <span className="font-mono text-[11px]">Provider:</span>
              </div>
              <select
                value={providerFilter}
                onChange={(e) => setProviderFilter(e.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent"
              >
                <option value="">All Providers</option>
                <option value="adyntel">Adyntel</option>
                <option value="meta_graph">Meta Graph API</option>
                <option value="apify">Apify Actor</option>
                <option value="metapi">Metapi</option>
                <option value="groq">Groq AI</option>
                <option value="gemini">Gemini Media</option>
                <option value="higgsfield">Higgsfield AI</option>
                <option value="scrapegraph">ScrapeGraph AI</option>
                <option value="system">System / Internal</option>
              </select>

              <div className="flex items-center gap-1.5 text-xs text-text-muted ml-2">
                <span className="font-mono text-[11px]">Operation:</span>
              </div>
              <select
                value={operationFilter}
                onChange={(e) => setOperationFilter(e.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent"
              >
                <option value="">All Operations</option>
                <option value="discover_search">Discover Search</option>
                <option value="ai_insight">AI Insight</option>
                <option value="pattern_synthesis">Pattern Synthesis</option>
                <option value="image_generate">Image Generation</option>
                <option value="video_generate">Video Generation</option>
                <option value="credit_grant">Credit Grant</option>
                <option value="plan_switch">Plan Switch</option>
              </select>
            </div>

            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Filter by User ID / Org..."
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                className="px-2.5 py-1 bg-surface border border-border rounded text-xs text-text font-mono focus:outline-none focus:border-accent w-48"
              />
              <Button size="xs" variant="primary" type="submit">
                Apply
              </Button>
            </form>
          </div>

          {/* Table */}
          <Panel className="flex min-w-0 flex-col overflow-hidden border border-border">
            <PanelHeader>
              <PanelTitle>Event Log Stream</PanelTitle>
              <Tag tone="default">{`Page ${page} · ${logs.length} entries`}</Tag>
            </PanelHeader>

            {loading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-9 w-full rounded" />
                ))}
              </div>
            ) : error ? (
              <ErrorState error={error} onRetry={() => fetchLogs(page)} />
            ) : logs.length === 0 ? (
              <div className="py-16 text-center text-text-muted">
                <ScrollText className="w-8 h-8 text-text-faint mx-auto mb-2 opacity-50" />
                <p className="text-sm font-semibold">No audit events match filters</p>
                <p className="text-xs text-text-faint mt-1">Try resetting the provider or operation criteria.</p>
              </div>
            ) : (
              <div className="min-w-0 overflow-auto">
                <table className="w-full min-w-[760px] table-fixed border-collapse text-left text-xs">
                  <thead className="sticky top-0 z-10 bg-surface-2 border-b border-border">
                    <tr>
                      <th scope="col" className="label-mono w-[110px] px-4 py-2.5 font-normal">Event ID</th>
                      <th scope="col" className="label-mono w-[130px] px-3 py-2.5 font-normal">Operation</th>
                      <th scope="col" className="label-mono w-[110px] px-3 py-2.5 font-normal">Provider</th>
                      <th scope="col" className="label-mono px-3 py-2.5 font-normal">User / Org</th>
                      <th scope="col" className="label-mono w-[85px] px-3 py-2.5 text-right font-normal">Credits</th>
                      <th scope="col" className="label-mono w-[90px] px-3 py-2.5 text-right font-normal">Est. Cost</th>
                      <th scope="col" className="label-mono w-[100px] px-4 py-2.5 text-right font-normal">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {logs.map((log) => (
                      <tr 
                        key={log.id} 
                        onClick={() => setSelectedLog(log)}
                        className="hover:bg-surface-2/40 transition cursor-pointer"
                      >
                        <td className="px-4 py-3 font-mono text-[11px] text-text-muted">
                          {log.id ? String(log.id).slice(0, 8) : "—"}
                        </td>
                        <td className="px-3 py-3">
                          <span className="font-mono font-medium text-text text-[11px] px-1.5 py-0.5 rounded bg-surface-2 border border-border">
                            {log.operation || "operation"}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <span className="font-mono text-accent text-[11px]">
                            {log.provider || "system"}
                          </span>
                        </td>
                        <td className="px-3 py-3 font-mono text-[11px] text-text-muted truncate">
                          {log.user_email || log.user_id || log.org_id || "System"}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-[11px] text-amber-400">
                          {log.credits_deducted ? `${Number(log.credits_deducted).toFixed(1)} cr` : "0.0 cr"}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-[11px] text-text-muted">
                          {log.cost_usd ? `$${Number(log.cost_usd).toFixed(4)}` : "$0.0000"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[11px] text-text-faint whitespace-nowrap">
                          {formatRelative(log.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            <div className="p-3 border-t border-border flex items-center justify-between bg-surface-2/60">
              <span className="text-xs font-mono text-text-muted">
                Showing page {page} of {Math.max(1, Math.ceil(total / 30))}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="xs"
                  variant="ghost"
                  disabled={page <= 1 || loading}
                  onClick={() => fetchLogs(page - 1)}
                >
                  <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                  Previous
                </Button>
                <Button
                  size="xs"
                  variant="ghost"
                  disabled={!hasMore || loading}
                  onClick={() => fetchLogs(page + 1)}
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* Modal detail */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface-2 p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-base font-bold text-text">Audit Event Inspector</h3>
                <span className="font-mono text-xs text-text-faint">{selectedLog.id}</span>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="text-text-muted hover:text-text p-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Operation</span>
                <span className="font-mono font-semibold text-text">{selectedLog.operation}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Provider</span>
                <span className="font-mono text-accent">{selectedLog.provider}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">User Email / ID</span>
                <span className="font-mono text-text">{selectedLog.user_email || selectedLog.user_id || "N/A"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Credits Deducted</span>
                <span className="font-mono text-amber-400">{selectedLog.credits_deducted || 0} cr</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Timestamp</span>
                <span className="font-mono text-text-muted">{selectedLog.created_at || "N/A"}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="xs" variant="primary" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AuditLogPage
