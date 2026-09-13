import React, { useState, useEffect } from "react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"
import { ErrorState, Skeleton } from "@/components/ui/States"
import { adminService } from "@/services"
import { formatRelative } from "@/lib/format"
import { 
  HeartPulse, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Server, 
  Database, 
  Cpu, 
  Globe,
  Radio,
  Clock
} from "lucide-react"

export function SystemHealthPage() {
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const fetchHealth = async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const data = await adminService.getSystemHealth()
      setHealthData(data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  const services = healthData?.services || []

  return (
    <div className="flex min-h-0 flex-1 flex-col font-sans">
      <BreadcrumbBar
        trail={["Console", "System", "Health"]}
        meta={loading ? "probing" : error ? "unavailable" : `overall ${healthData?.state || "operational"}`}
        actions={
          <Button size="xs" variant="ghost" onClick={() => fetchHealth(false)} disabled={loading || refreshing}>
            <RefreshCw className={`mr-1 h-3 w-3 ${loading || refreshing ? "animate-spin" : ""}`} />
            Run Live Diagnostics
          </Button>
        }
      />

      <div className="min-h-0 flex-1 overflow-auto p-4 md:p-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-text flex items-center gap-2.5">
                <HeartPulse className="w-5 h-5 text-accent" />
                System Health & Infrastructure Probes
              </h1>
              <p className="text-xs text-text-muted mt-0.5">
                Live end-to-end health monitoring across Postgres pooler, AI reasoning LPUs, and scraping nodes.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Tag tone={healthData?.state === "operational" ? "success" : healthData?.state === "degraded" ? "warning" : "danger"}>
                Status: {healthData?.state || "operational"}
              </Tag>
            </div>
          </div>

          {/* Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-border bg-surface-2 space-y-2">
              <div className="flex items-center gap-2 text-text font-semibold text-sm">
                <Database className="w-4 h-4 text-cyan-400" />
                Database Engine
              </div>
              <p className="text-xs text-text-muted">
                Neon Postgres Serverless with PgBouncer connection pooling and zero-prepared-statement tuning.
              </p>
              <div className="pt-2 flex items-center justify-between text-xs font-mono">
                <span className="text-text-faint">Type: Multi-region Pooler</span>
                <span className="text-emerald-400">Online</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-surface-2 space-y-2">
              <div className="flex items-center gap-2 text-text font-semibold text-sm">
                <Cpu className="w-4 h-4 text-accent" />
                AI Inference Stack
              </div>
              <p className="text-xs text-text-muted">
                Groq LPUs running Llama-3.3-70b-versatile, Mixtral 8x7b, and OpenRouter multi-model fallbacks.
              </p>
              <div className="pt-2 flex items-center justify-between text-xs font-mono">
                <span className="text-text-faint">Throughput: High Concurrency</span>
                <span className="text-emerald-400">Ready</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-surface-2 space-y-2">
              <div className="flex items-center gap-2 text-text font-semibold text-sm">
                <Globe className="w-4 h-4 text-indigo-400" />
                Scraper Mesh
              </div>
              <p className="text-xs text-text-muted">
                Adyntel, Meta Official Graph API, and Apify cloud actors with automatic rate-limit cascade.
              </p>
              <div className="pt-2 flex items-center justify-between text-xs font-mono">
                <span className="text-text-faint">Failover: Automated</span>
                <span className="text-emerald-400">Standby</span>
              </div>
            </div>
          </div>

          {/* Table */}
          <Panel className="flex min-w-0 flex-col overflow-hidden border border-border">
            <PanelHeader>
              <PanelTitle>Active Health Diagnostic Results</PanelTitle>
              <Tag tone="default">{`${services.length} services monitored`}</Tag>
            </PanelHeader>

            {loading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded" />
                ))}
              </div>
            ) : error ? (
              <ErrorState error={error} onRetry={() => fetchHealth(false)} />
            ) : (
              <div className="min-w-0 overflow-auto">
                <table className="w-full min-w-[650px] table-fixed border-collapse text-left text-xs">
                  <thead className="sticky top-0 z-10 bg-surface-2 border-b border-border">
                    <tr>
                      <th scope="col" className="label-mono px-4 py-2.5 font-normal">Service Name</th>
                      <th scope="col" className="label-mono w-[110px] px-3 py-2.5 font-normal">State</th>
                      <th scope="col" className="label-mono px-3 py-2.5 font-normal">Status Message</th>
                      <th scope="col" className="label-mono w-[100px] px-3 py-2.5 text-right font-normal">Latency</th>
                      <th scope="col" className="label-mono w-[110px] px-4 py-2.5 text-right font-normal">Last Probe</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {services.map((s) => (
                      <tr key={s.id} className="hover:bg-surface-2/40 transition">
                        <td className="px-4 py-3 font-semibold text-text">
                          {s.name}
                        </td>
                        <td className="px-3 py-3">
                          <Tag tone={s.status === "success" ? "success" : s.status === "warning" ? "warning" : "danger"}>
                            {s.status}
                          </Tag>
                        </td>
                        <td className="px-3 py-3 text-text-muted">
                          {s.detail}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-[11px] text-text-muted">
                          {s.latency_ms !== null && s.latency_ms !== undefined ? `${s.latency_ms}ms` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[11px] text-text-faint">
                          {formatRelative(s.last_checked)}
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
    </div>
  )
}

export default SystemHealthPage
