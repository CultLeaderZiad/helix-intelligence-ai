import { useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  Eye,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Trash2,
  Sparkles,
  PenLine,
  CircleSlash,
} from "lucide-react"

import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States"
import { useMonitors } from "@/hooks/useMonitors"

const CADENCES = [
  { value: "every_6h", label: "Every 6 hours" },
  { value: "every_12h", label: "Every 12 hours" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
]

const EVENT_META = {
  new_ad: { label: "New ad", tone: "success", icon: Sparkles },
  copy_changed: { label: "Copy changed", tone: "warning", icon: PenLine },
  killed_ad: { label: "Stopped", tone: "danger", icon: CircleSlash },
}

function formatWhen(value) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  const diffMs = date.getTime() - Date.now()
  const absMin = Math.round(Math.abs(diffMs) / 60000)
  if (absMin < 1) return "now"
  if (absMin < 60) return diffMs > 0 ? `in ${absMin}m` : `${absMin}m ago`
  const hours = Math.round(absMin / 60)
  if (hours < 48) return diffMs > 0 ? `in ${hours}h` : `${hours}h ago`
  return date.toLocaleDateString()
}

function RunSummary({ monitor }) {
  const run = monitor.last_run
  if (!run) {
    return <span className="text-text-faint">Waiting for its first run</span>
  }
  if (run.status === "running") {
    return <span className="text-accent">Running now…</span>
  }
  if (run.status === "skipped") {
    return <span className="text-warning">Skipped — {run.error || run.skipped_reason}</span>
  }
  if (run.status === "failed") {
    return <span className="text-danger">Last run failed — {run.error}</span>
  }
  if (run.is_baseline) {
    return (
      <span className="text-text-muted">
        Baseline recorded from {run.creatives_seen} ads. Changes are reported from the next run.
      </span>
    )
  }
  if (run.skipped_reason === "empty_result") {
    return (
      <span className="text-warning">
        Last run returned no ads, so nothing was compared. Reported as inconclusive rather than
        treating every ad as stopped.
      </span>
    )
  }
  const total = run.new_count + run.changed_count + run.killed_count
  if (total === 0) {
    return <span className="text-text-muted">No changes across {run.creatives_seen} ads</span>
  }
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {run.new_count > 0 ? <Tag tone="success">{run.new_count} new</Tag> : null}
      {run.changed_count > 0 ? <Tag tone="warning">{run.changed_count} changed</Tag> : null}
      {run.killed_count > 0 ? <Tag tone="danger">{run.killed_count} stopped</Tag> : null}
      <span className="text-text-faint">of {run.creatives_seen} ads</span>
    </span>
  )
}

function CreateMonitorForm({ onCreate, busy }) {
  const [query, setQuery] = useState("")
  const [cadence, setCadence] = useState("daily")
  const [notifyEmail, setNotifyEmail] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const clean = query.trim()
    if (!clean) return
    const ok = await onCreate({
      query: clean,
      name: clean,
      cadence,
      notify_in_app: true,
      notify_email: notifyEmail,
    })
    if (ok) setQuery("")
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Brand or keyword to watch (e.g. gymshark)"
        className="h-8 min-w-[240px] flex-1 rounded-sm border border-border bg-surface-2 px-2.5 text-xs text-text placeholder:text-text-faint focus:border-border-strong focus:outline-none"
      />
      <select
        value={cadence}
        onChange={(e) => setCadence(e.target.value)}
        className="h-8 rounded-sm border border-border bg-surface-2 px-2 text-xs text-text focus:outline-none"
      >
        {CADENCES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
      <label className="flex items-center gap-1.5 text-xs text-text-muted">
        <input
          type="checkbox"
          checked={notifyEmail}
          onChange={(e) => setNotifyEmail(e.target.checked)}
          className="accent-accent"
        />
        Email me
      </label>
      <Button type="submit" size="sm" variant="primary" disabled={busy || !query.trim()}>
        <Plus className="h-3.5 w-3.5" />
        Add monitor
      </Button>
    </form>
  )
}

function MonitorRow({ monitor, onRun, onToggle, onDelete, focused }) {
  const paused = monitor.status === "paused"
  const running = monitor.last_run?.status === "running"

  return (
    <div
      id={`monitor-${monitor.id}`}
      className={`flex flex-col gap-2 border-b border-border px-3 py-2.5 last:border-b-0 ${
        focused ? "bg-accent/5 ring-1 ring-accent/40" : ""
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[13px] font-medium text-text">{monitor.name}</span>
        <Tag tone={paused ? "default" : "accent"}>{paused ? "Paused" : monitor.cadence.replace("_", " ")}</Tag>
        {monitor.notify_email ? <Tag tone="info">Email</Tag> : null}
        <span className="ml-auto font-mono text-[11px] text-text-faint">
          {paused ? "—" : `Next ${formatWhen(monitor.next_run_at)}`}
        </span>
        <div className="flex items-center gap-1">
          <Button
            size="icon-sm"
            variant="ghost"
            title="Run now"
            disabled={running}
            onClick={() => onRun(monitor.id)}
          >
            <RefreshCw className={running ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            title={paused ? "Resume" : "Pause"}
            onClick={() => onToggle(monitor)}
          >
            {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
          </Button>
          <Button size="icon-sm" variant="ghost" title="Delete" onClick={() => onDelete(monitor)}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-mono text-[11px] text-text-faint">"{monitor.query}"</span>
        <span className="text-text-faint">·</span>
        <RunSummary monitor={monitor} />
      </div>

      {paused && monitor.paused_reason ? (
        <p className="text-xs text-warning">{monitor.paused_reason}</p>
      ) : null}
    </div>
  )
}

function EventRow({ event }) {
  const meta = EVENT_META[event.type] ?? { label: event.type, tone: "default", icon: Eye }
  const Icon = meta.icon
  const previous = event.previous

  return (
    <div className="flex gap-2.5 border-b border-border px-3 py-2.5 last:border-b-0">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-text-faint" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <Tag tone={meta.tone}>{meta.label}</Tag>
          <span className="font-mono text-[11px] text-text-faint">{formatWhen(event.created_at)}</span>
          {event.landing_domain ? (
            <span className="font-mono text-[11px] text-text-faint">{event.landing_domain}</span>
          ) : null}
        </div>
        <p className="truncate text-[13px] text-text">{event.headline || "(no headline)"}</p>
        {event.body ? (
          <p className="line-clamp-2 text-xs text-text-muted">{event.body}</p>
        ) : null}
        {event.type === "copy_changed" && previous ? (
          <div className="mt-0.5 flex flex-col gap-0.5 border-l-2 border-border pl-2">
            <p className="line-clamp-2 text-[11px] text-text-faint line-through">
              {previous.body || previous.headline || "(was empty)"}
            </p>
            <p className="line-clamp-2 text-[11px] text-text-muted">{event.body || event.headline}</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function MonitorsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusId = searchParams.get("id")
  const {
    monitors,
    events,
    loading,
    error,
    actionError,
    refresh,
    createMonitor,
    updateMonitor,
    deleteMonitor,
    runNow,
  } = useMonitors()

  const [busy, setBusy] = useState(false)

  const activeCount = useMemo(
    () => monitors.filter((m) => m.status === "active").length,
    [monitors],
  )

  async function guard(fn) {
    setBusy(true)
    try {
      return await fn()
    } finally {
      setBusy(false)
    }
  }

  function handleToggle(monitor) {
    return guard(() =>
      updateMonitor(monitor.id, { status: monitor.status === "paused" ? "active" : "paused" }),
    )
  }

  function handleDelete(monitor) {
    if (!window.confirm(`Delete the monitor for "${monitor.query}"? Its change history goes too.`)) {
      return undefined
    }
    return guard(() => deleteMonitor(monitor.id))
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar
        trail={["Helix", "Monitors", "Scheduled Competitor Watches"]}
        meta={`${activeCount} active · ${events.length} recent changes`}
        actions={
          <Button size="xs" variant="outline" onClick={() => refresh()}>
            Refresh
          </Button>
        }
      />

      <div className="flex flex-col gap-4 p-6">
        <Panel>
          <PanelHeader>
            <PanelTitle>New monitor</PanelTitle>
            <span className="font-mono text-[11px] text-text-faint">
              Each run costs the same as one Discover search
            </span>
          </PanelHeader>
          <PanelBody>
            <CreateMonitorForm onCreate={(p) => guard(() => createMonitor(p))} busy={busy} />
            {actionError ? (
              <p className="mt-2 text-xs text-danger">
                {actionError.message || "That action could not be completed."}
              </p>
            ) : null}
          </PanelBody>
        </Panel>

        {error ? (
          <ErrorState error={error} onRetry={() => refresh()} />
        ) : loading ? (
          <SkeletonRows rows={4} />
        ) : (
          <>
            <Panel>
              <PanelHeader>
                <PanelTitle>Monitors</PanelTitle>
              </PanelHeader>
              {monitors.length === 0 ? (
                <EmptyState
                  icon={Eye}
                  status="nothing watched"
                  title="No monitors yet"
                  description="A monitor re-runs a Discover search on a schedule and tells you what changed since last time — new ads, copy edits, and ads that stopped running."
                  action={
                    <Button size="sm" variant="outline" onClick={() => navigate("/discover")}>
                      Explore in Discover first
                    </Button>
                  }
                />
              ) : (
                <div className="flex flex-col">
                  {monitors.map((m) => (
                    <MonitorRow
                      key={m.id}
                      monitor={m}
                      focused={m.id === focusId}
                      onRun={(id) => guard(() => runNow(id))}
                      onToggle={handleToggle}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              )}
            </Panel>

            <Panel>
              <PanelHeader>
                <PanelTitle>Change feed</PanelTitle>
                <span className="font-mono text-[11px] text-text-faint">{events.length} events</span>
              </PanelHeader>
              {events.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  status="no changes yet"
                  title="Nothing has changed yet"
                  description="The first run of a monitor records a baseline and reports nothing. From the second run onward, anything that differs shows up here."
                />
              ) : (
                <div className="flex flex-col">
                  {events.map((e) => (
                    <EventRow key={e.id} event={e} />
                  ))}
                </div>
              )}
            </Panel>
          </>
        )}
      </div>
    </div>
  )
}

export default MonitorsPage
