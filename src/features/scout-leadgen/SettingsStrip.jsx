import React from "react"
import { Bot, Globe, ShieldCheck, Zap, Server } from "lucide-react"

/**
 * SettingsStrip — renders ONLY what GET /worker/health returns.
 * No theater switches: every value here is real backend truth.
 * Includes the ToS/robots/proxy help copy (spec 9).
 */
function Badge({ ok, on, off }) {
  return (
    <span className={ok ? "text-success font-bold" : "text-text-faint font-bold"}>{ok ? on : off}</span>
  )
}

export function SettingsStrip({ health }) {
  if (!health) {
    return (
      <div className="rounded-[4px] border border-border bg-surface/60 px-4 py-2 font-mono text-[11px] text-text-muted">
        worker status · loading…
      </div>
    )
  }
  const online = health.worker === "online"
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-[4px] border border-border bg-surface/60 px-4 py-2 font-mono text-[11px] text-text-muted">
      <span className="flex items-center gap-1.5">
        <Bot className="h-3.5 w-3.5" />
        worker: <Badge ok={online} on="online" off="offline" />
        {health.scrapling_version && <span className="text-text-faint">· scrapling {health.scrapling_version}</span>}
      </span>
      <span className="text-text-faint">|</span>
      <span className="flex items-center gap-1.5">
        <Server className="h-3.5 w-3.5" />
        browsers: <Badge ok={health.browsers_ready} on="ready" off="not ready" />
      </span>
      <span className="text-text-faint">|</span>
      <span className="flex items-center gap-1.5">
        <Globe className="h-3.5 w-3.5" />
        proxy: <Badge ok={health.proxy === "configured"} on="configured" off="off" />
      </span>
      <span className="text-text-faint">|</span>
      <span className="flex items-center gap-1.5">
        <ShieldCheck className="h-3.5 w-3.5" />
        robots default: <Badge ok={health.robots_default} on="on" off="off" />
      </span>
      <span className="text-text-faint">|</span>
      <span className="flex items-center gap-1.5">
        <Zap className="h-3.5 w-3.5" />
        engine: <span className="text-white font-bold">{health.engine_default || "stealth"}</span>
      </span>
      <span className="text-text-faint">|</span>
      <span>
        queue: <span className="text-white font-bold tnum">{health.queue_depth ?? 0}</span>
      </span>
      <span className="ml-auto hidden lg:inline text-text-faint normal-case tracking-normal">
        Public pages only · robots.txt honored · use proxies at your own cost · MENA public B2B data
      </span>
    </div>
  )
}

export default SettingsStrip
