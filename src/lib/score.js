import { SCORE_THRESHOLD } from "./constants"

/**
 * Pure scoring helpers. Presentational components receive the *result*
 * of these functions, never the raw thresholds — so if the backend
 * starts returning precomputed tiers, only this file changes.
 */

/** @returns {'strong'|'moderate'|'weak'|'none'} */
export function scoreTier(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "none"
  if (value >= SCORE_THRESHOLD.strong) return "strong"
  if (value >= SCORE_THRESHOLD.moderate) return "moderate"
  return "weak"
}

/** Tailwind text colour per tier. Accent is reserved for "strong" only. */
export function scoreTextClass(value) {
  const tier = scoreTier(value)
  return {
    strong: "text-accent",
    moderate: "text-text",
    weak: "text-text-muted",
    none: "text-text-faint",
  }[tier]
}

/** Tailwind fill per tier, for bars. */
export function scoreFillClass(value) {
  const tier = scoreTier(value)
  return {
    strong: "bg-accent",
    moderate: "bg-border-strong",
    weak: "bg-border",
    none: "bg-transparent",
  }[tier]
}

export function isScored(creative) {
  return creative?.scores?.composite !== null && creative?.scores?.composite !== undefined
}
