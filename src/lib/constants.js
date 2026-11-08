/** Enumerations mirrored from the (future) FastAPI schema. */

export const PLATFORMS = [
  { value: "meta", label: "Meta" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "reddit", label: "Reddit" },
]

export const FORMATS = [
  { value: "video", label: "Video" },
  { value: "image", label: "Image" },
  { value: "carousel", label: "Carousel" },
  { value: "text", label: "Text" },
]

export const COUNTRIES = [
  { value: "ALL", label: "All Countries" },
  { value: "US", label: "United States" },
  { value: "GB", label: "United Kingdom" },
  { value: "CA", label: "Canada" },
  { value: "AU", label: "Australia" },
  { value: "DE", label: "Germany" },
  { value: "FR", label: "France" },
]

export const SPEND_BANDS = [
  { value: "low", label: "$" },
  { value: "mid", label: "$$" },
  { value: "high", label: "$$$" },
  { value: "very_high", label: "$$$$" },
]

export const SORT_OPTIONS = [
  { value: "days_active_desc", label: "Days active" },
  { value: "first_seen_desc", label: "Newest" },
  { value: "composite_desc", label: "Text rubric (0–10)" },
  { value: "hook_desc", label: "Hook rubric (0–10)" },
  { value: "impressions_desc", label: "Meta reach (upper bound)" },
]

/** Score thresholds drive accent usage — accent means "notable", not "exists". */
export const SCORE_THRESHOLD = {
  strong: 8.0,
  moderate: 6.0,
}

/**
 * Discover job statuses (scrape_jobs.status). Mirrors SCRAPE_JOB in
 * backend/app/core/state_machines.py; see docs/w8/state-machines.md.
 * "canceled" (US spelling) is the work-item value and is accepted as a
 * legacy alias for "cancelled".
 */
export const JOB_STATUS = {
  QUEUED: "queued",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
  CANCELLED: "cancelled",
  TIMED_OUT: "timed_out",
}

export const JOB_STATUS_CANCELED_ALIAS = "canceled"

export const JOB_TERMINAL_STATUSES = Object.freeze([
  JOB_STATUS.SUCCEEDED,
  JOB_STATUS.FAILED,
  JOB_STATUS.CANCELLED,
  JOB_STATUS_CANCELED_ALIAS,
  JOB_STATUS.TIMED_OUT,
])

/** @param {string | null | undefined} status */
export function isJobCancelled(status) {
  return status === JOB_STATUS.CANCELLED || status === JOB_STATUS_CANCELED_ALIAS
}

/** @param {string | null | undefined} status */
export function isJobTerminal(status) {
  return typeof status === "string" && JOB_TERMINAL_STATUSES.includes(status)
}
