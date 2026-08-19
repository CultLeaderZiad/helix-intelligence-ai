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

export const SPEND_BANDS = [
  { value: "low", label: "$" },
  { value: "mid", label: "$$" },
  { value: "high", label: "$$$" },
  { value: "very_high", label: "$$$$" },
]

export const SORT_OPTIONS = [
  { value: "composite_desc", label: "Composite score" },
  { value: "hook_desc", label: "Hook score" },
  { value: "days_active_desc", label: "Days active" },
  { value: "first_seen_desc", label: "Newest" },
  { value: "impressions_desc", label: "Est. impressions" },
]

/** Score thresholds drive accent usage — accent means "notable", not "exists". */
export const SCORE_THRESHOLD = {
  strong: 8.0,
  moderate: 6.0,
}

export const JOB_STATUS = {
  QUEUED: "queued",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
}
