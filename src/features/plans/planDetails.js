import { localizedList } from "@/i18n/pricing"

const LIMIT_ORDER = [
  "searches_per_day", "monitors", "records_per_month", "agent_messages_per_day",
  "agent_generations_per_day", "teardowns_per_day", "alerts_per_day", "alert_telegram_chats", "alert_webhooks",
]

/**
 * What a plan really enforces, from its own `limits`. A limit the plan does not
 * set is left out: nothing is invented and nothing is shown as a default.
 * @param {Record<string, number | null> | null | undefined} limits
 * @param {Record<string, string>} labels
 */
export function limitLines(limits, labels) {
  if (!limits) return []
  return LIMIT_ORDER
    .filter((key) => Number.isFinite(limits[key]) && labels[key])
    .map((key) => `${labels[key]}: ${Number(limits[key]).toLocaleString("en-US")}`)
}

/**
 * The feature list of a plan card: the admin's own text when there is some,
 * otherwise the plan's real feature flags. Never a hard-coded list.
 */
export function featureLines(plan, lang, copy) {
  const written = localizedList(plan.pricing?.features, lang)
  if (written.length) return written
  return (plan.feature_flags || []).map((key) => copy.features[key]).filter(Boolean)
}
