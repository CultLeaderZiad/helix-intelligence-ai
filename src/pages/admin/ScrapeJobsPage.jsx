import React, { useState, useEffect, useMemo } from "react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"
import { ErrorState, Skeleton } from "@/components/ui/States"
import { adminService } from "@/services"
import { formatInt, formatDuration, formatRelative } from "@/lib/format"
import { 
  ListChecks, 
  Search, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Play, 
  ExternalLink,
  Layers,
  Database,
  ArrowUpDown
} from "lucide-react"

const STATUS_TONE = {
  queued: "default",
  running: "info",
  succeeded: "success",
  failed: "danger",
}

export function ScrapeJobsPage() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedJob, setSelectedJob] = useState(null)

  const fetchJobs = async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const res = await adminService.listRecentJobs()
      setJobs(Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : [])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  // Auto-refresh every 12 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return
    const timer = setInterval(() => {
      fetchJobs(true)
    }, 12000)
    return () => clearInterval(timer)
  }, [autoRefresh])

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const matchesSearch = 
        !searchTerm ||
        (job.query && job.query.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (job.organization && job.organization.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (job.job_id && job.job_id.toLowerCase().includes(searchTerm.toLowerCase()))

      const matchesStatus = statusFilter === "all" || job.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [jobs, searchTerm, statusFilter])

  const counts = useMemo(() => {
    const total = jobs.length
    const running = jobs.filter((j) => j.status === "running").length
    const succeeded = jobs.filter((j) => j.status === "succeeded").length
    const failed = jobs.filter((j) => j.status === "failed").length
    const totalRecords = jobs.reduce((acc, j) => acc + (j.records || 0), 0)
    return { total, running, succeeded, failed, totalRecords }
  }, [jobs])

  return (
    <div className="w-full flex-1 flex flex-col font-sans">
      <BreadcrumbBar
        trail={["Console", "Data", "Scrape Jobs"]}
        meta={loading ? "loading" : error ? "unavailable" : `live (${jobs.length} jobs)`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`text-xs px-2.5 py-1 rounded font-mono border transition ${
                autoRefresh 
                  ? "bg-accent/10 border-accent/30 text-accent" 
                  : "bg-surface-2 border-border text-text-muted"
              }`}
            >
              {autoRefresh ? "● Auto-refresh ON (12s)" : "○ Auto-refresh OFF"}
            </button>
            <Button size="xs" variant="ghost" onClick={() => fetchJobs(false)} disabled={loading || refreshing}>
              <RefreshCw className={`mr-1 h-3 w-3 ${loading || refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        }
      />

      <div className="p-4 md:p-6 w-full">
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          {/* Header Summary */}
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-text flex items-center gap-2.5">
              <ListChecks className="w-5 h-5 text-accent" />
              Real-Time Scrape Jobs & Ingestion Pipeline
            </h1>
            <p className="text-xs text-text-muted">
              Live stream of cross-tenant ad intelligence scraping operations, execution duration, gathered records, and error traces.
            </p>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface-2 p-3">
              <span className="label-mono text-text-faint">Total Jobs</span>
              <span className="font-mono text-lg font-bold text-text">{formatInt(counts.total)}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface-2 p-3">
              <span className="label-mono text-text-faint">Active Running</span>
              <span className="font-mono text-lg font-bold text-cyan-400">{formatInt(counts.running)}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface-2 p-3">
              <span className="label-mono text-text-faint">Succeeded</span>
              <span className="font-mono text-lg font-bold text-emerald-400">{formatInt(counts.succeeded)}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface-2 p-3">
              <span className="label-mono text-text-faint">Failed / Empty</span>
              <span className="font-mono text-lg font-bold text-rose-400">{formatInt(counts.failed)}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface-2 p-3 col-span-2 sm:col-span-1">
              <span className="label-mono text-text-faint">Records Ingested</span>
              <span className="font-mono text-lg font-bold text-accent">{formatInt(counts.totalRecords)}</span>
            </div>
          </div>

          {/* Filters and Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-faint" />
              <input
                type="text"
                placeholder="Filter by query, tenant, or job ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-surface-2 border border-border rounded-lg text-text text-xs font-mono focus:outline-none focus:border-accent"
              />
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {["all", "running", "succeeded", "failed", "queued"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 text-xs font-mono rounded-md border transition capitalize ${
                    statusFilter === st
                      ? "bg-surface-3 text-text border-accent/40 font-semibold"
                      : "bg-surface text-text-muted border-border hover:bg-surface-2"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {/* Main Table Panel */}
          <Panel className="flex min-w-0 flex-col overflow-hidden border border-border">
            <PanelHeader>
              <PanelTitle>Live Execution Table</PanelTitle>
              <Tag tone="default">{`${filteredJobs.length} of ${jobs.length} jobs`}</Tag>
            </PanelHeader>

            {loading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-9 w-full rounded" />
                ))}
              </div>
            ) : error ? (
              <ErrorState error={error} onRetry={() => fetchJobs(false)} />
            ) : filteredJobs.length === 0 ? (
              <div className="py-16 text-center text-text-muted">
                <ListChecks className="w-8 h-8 text-text-faint mx-auto mb-2 opacity-50" />
                <p className="text-sm font-semibold">No scrape jobs match filter</p>
                <p className="text-xs text-text-faint mt-1">Try resetting the search or status criteria.</p>
              </div>
            ) : (
              <div className="min-w-0 overflow-auto">
                <table className="w-full min-w-[700px] table-fixed border-collapse text-left text-xs">
                  <thead className="sticky top-0 z-10 bg-surface-2/80 backdrop-blur border-b border-border">
                    <tr>
                      <th scope="col" className="label-mono w-[110px] px-4 py-2.5 font-normal">Job ID</th>
                      <th scope="col" className="label-mono w-[150px] px-3 py-2.5 font-normal">Tenant Org</th>
                      <th scope="col" className="label-mono px-3 py-2.5 font-normal">Search Query</th>
                      <th scope="col" className="label-mono w-[95px] px-3 py-2.5 font-normal">Status</th>
                      <th scope="col" className="label-mono w-[85px] px-3 py-2.5 text-right font-normal">Records</th>
                      <th scope="col" className="label-mono w-[85px] px-3 py-2.5 text-right font-normal">Duration</th>
                      <th scope="col" className="label-mono w-[95px] px-4 py-2.5 text-right font-normal">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredJobs.map((job) => (
                      <tr 
                        key={job.job_id} 
                        onClick={() => setSelectedJob(job)}
                        className="hover:bg-surface-3/50 transition cursor-pointer"
                      >
                        <td className="px-4 py-3 font-mono text-[11px] text-text-muted">
                          {job.job_id.length > 12 ? `${job.job_id.slice(0, 8)}...` : job.job_id}
                        </td>
                        <td className="px-3 py-3">
                          <span className="block truncate font-medium text-text">
                            {job.organization || "Default Org"}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-text truncate max-w-[280px]">
                              {job.query}
                            </span>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <Tag tone={STATUS_TONE[job.status] ?? "default"}>
                            {job.status}
                          </Tag>
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-[11px] text-text-muted">
                          {job.records ? formatInt(job.records) : "0"}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-[11px] text-text-muted">
                          {job.duration_ms ? formatDuration(job.duration_ms) : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[11px] text-text-faint whitespace-nowrap">
                          {formatRelative(job.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-surface-2 p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-base font-bold text-text">Scrape Job Details</h3>
                <span className="font-mono text-xs text-text-faint">{selectedJob.job_id}</span>
              </div>
              <button 
                onClick={() => setSelectedJob(null)}
                className="text-text-muted hover:text-text p-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Query</span>
                <span className="font-semibold text-text">{selectedJob.query}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Tenant Organization</span>
                <span className="text-text">{selectedJob.organization}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Status</span>
                <Tag tone={STATUS_TONE[selectedJob.status] ?? "default"}>{selectedJob.status}</Tag>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Records Ingested</span>
                <span className="font-mono text-accent">{formatInt(selectedJob.records || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Execution Duration</span>
                <span className="font-mono text-text">{formatDuration(selectedJob.duration_ms || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-text-muted">Created</span>
                <span className="font-mono text-text-muted">{selectedJob.created_at || "N/A"}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="xs" variant="primary" onClick={() => setSelectedJob(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ScrapeJobsPage
