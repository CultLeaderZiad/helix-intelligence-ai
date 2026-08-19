/**
 * Pure display formatters. No React, no service imports.
 * Every numeric readout in the UI routes through here so that
 * precision and units stay consistent across surfaces.
 */

export function formatCompact(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—"
  const abs = Math.abs(n)
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export function formatInt(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—"
  return new Intl.NumberFormat("en-US").format(n)
}

export function formatPercent(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—"
  return `${n.toFixed(digits)}%`
}

export function formatScore(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—"
  return n.toFixed(1)
}

/** ISO date -> "12 Mar 26" */
export function formatDate(iso) {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
  }).format(d)
}

/** ISO date -> "3d ago" / "5h ago" */
export function formatRelative(iso) {
  if (!iso) return "—"
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return "—"
  const diff = Date.now() - then
  const mins = Math.round(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.round(days / 30)
  return `${months}mo ago`
}

export function formatDuration(ms) {
  if (ms === null || ms === undefined) return "—"
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function formatSpendBand(band) {
  const map = {
    low: "$",
    mid: "$$",
    high: "$$$",
    very_high: "$$$$",
  }
  return map[band] ?? "—"
}
