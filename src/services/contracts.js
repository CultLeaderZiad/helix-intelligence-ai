/**
 * ============================================================
 * SERVICE CONTRACTS
 * ============================================================
 * JSDoc typedefs only — no runtime code. This is the single
 * agreed shape between the React client and the future FastAPI
 * backend. Editors get full intellisense without TypeScript.
 *
 * Every mock implementation and every HTTP implementation must
 * satisfy these shapes exactly. If the backend diverges, this
 * file changes first and the compiler-of-record is code review.
 *
 * Conventions (chosen to match FastAPI + Pydantic defaults):
 *   - snake_case keys
 *   - ISO-8601 UTC timestamps
 *   - list endpoints return a pagination envelope, never a bare array
 *   - long work returns a Job, never a blocking response
 * ============================================================
 */

/**
 * @typedef {Object} Scores
 * @property {number|null} hook
 * @property {number|null} clarity
 * @property {number|null} retention
 * @property {number|null} composite
 */

/**
 * @typedef {Object} CreativeMetrics
 * @property {number|null} impressions_est
 * @property {'low'|'mid'|'high'|'very_high'|null} spend_band
 * @property {number|null} engagement_rate
 * @property {number|null} ctr_est
 */

/**
 * @typedef {Object} Creative
 * @property {string} id
 * @property {string} brand_id
 * @property {'meta'|'tiktok'|'youtube'|'linkedin'|'reddit'} platform
 * @property {'video'|'image'|'carousel'|'text'} format
 * @property {string} headline
 * @property {string} body
 * @property {string} cta
 * @property {string|null} landing_domain
 * @property {string|null} thumbnail_ratio
 * @property {number|null} duration_seconds
 * @property {string} first_seen
 * @property {string} last_seen
 * @property {number} days_active
 * @property {number} variant_count
 * @property {Scores} scores
 * @property {CreativeMetrics} metrics
 * @property {string[]} pattern_ids
 */

/**
 * @typedef {Object} Brand
 * @property {string} id
 * @property {string} name
 * @property {string} domain
 * @property {string} category
 * @property {number} ad_count
 * @property {string} first_seen
 */

/**
 * @typedef {Object} Pattern
 * @property {string} id
 * @property {string} label
 * @property {string} family
 * @property {number} prevalence
 * @property {number} lift_index
 */

/**
 * @typedef {Object} Insight
 * @property {string} id
 * @property {string} creative_id
 * @property {'hook_analysis'|'risk'|'opportunity'} kind
 * @property {string} title
 * @property {string} summary
 * @property {number} confidence
 * @property {string[]} evidence_creative_ids
 * @property {string} generated_at
 * @property {string} model_version
 */

/**
 * Async work handle. Returned immediately by any operation that will be
 * worker-backed in production (discovery scrapes, batch scoring, generation).
 *
 * @typedef {Object} Job
 * @property {string} job_id
 * @property {'queued'|'running'|'succeeded'|'failed'} status
 * @property {number} progress            0..1
 * @property {string} stage               stage key, see DISCOVERY_STAGES
 * @property {string} stage_label
 * @property {number} stage_index
 * @property {number} stages_total
 * @property {number} records_found
 * @property {number} elapsed_ms
 * @property {string} created_at
 * @property {string|null} completed_at
 * @property {string|null} error
 */

/**
 * Standard list envelope for every collection endpoint.
 *
 * @typedef {Object} Paginated
 * @property {Array<any>} items
 * @property {number} total
 * @property {number} page
 * @property {number} page_size
 * @property {boolean} has_more
 * @property {number} [took_ms]
 */

/**
 * @typedef {Object} SearchParams
 * @property {string} [query]
 * @property {Object} [filters]
 * @property {string[]} [filters.platforms]
 * @property {string[]} [filters.formats]
 * @property {string[]} [filters.spend_bands]
 * @property {number} [filters.min_score]
 * @property {number} [filters.min_days_active]
 * @property {string} [sort]
 * @property {number} [page]
 * @property {number} [page_size]
 */

/**
 * Normalized error thrown by every service implementation.
 *
 * @typedef {Object} ServiceErrorShape
 * @property {string} message
 * @property {number|null} status
 * @property {string} code
 */

export {}
