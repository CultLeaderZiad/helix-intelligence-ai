/**
 * Creative insight derivation.
 *
 * "Why this ad matters" is NOT generated text — every line is computed
 * from fields the detail endpoint actually returned. When the FastAPI
 * insight endpoint ships, this module is replaced by its response and
 * the UI does not change.
 *
 * Derivations:
 * - reasons     -> attributed patterns ranked by lift_index (max 3)
 * - longevity   -> days_active, verbatim
 * - confidence  -> composite score scaled by score coverage: a creative
 *                  scored on all four dimensions earns full weight, a
 *                  partially scored one is discounted. Range 0–99.
 */

const SCORE_KEYS = ["hook", "clarity", "retention", "composite"]

export function deriveInsight(creative) {
  if (!creative) return null

  const composite = creative.scores?.composite
  if (composite === null || composite === undefined) return null

  const scoredCount = SCORE_KEYS.filter(
    (k) => creative.scores?.[k] !== null && creative.scores?.[k] !== undefined,
  ).length
  const coverage = scoredCount / SCORE_KEYS.length

  const confidence = Math.min(
    99,
    Math.round(composite * 10 * (0.7 + 0.3 * coverage)),
  )

  const reasons = [...(creative.patterns ?? [])]
    .sort((a, b) => b.lift_index - a.lift_index)
    .slice(0, 3)
    .map((p) => ({
      id: p.id,
      label: p.label,
      family: p.family,
      lift: p.lift_index,
      prevalence: p.prevalence,
    }))

  if (reasons.length === 0) return null

  return {
    daysActive: creative.days_active ?? null,
    reasons,
    confidence,
  }
}
