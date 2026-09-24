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
 * @property {'service_restart'|'error'|null} [failure_kind]  why it failed,
 *   so the UI can separate "the backend restarted" from "your search broke"
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

/**
 * @typedef {Object} MediaJob
 * @property {string} job_id
 * @property {'queued'|'running'|'succeeded'|'failed'|'nsfw'|'canceled'} status
 * @property {number} progress          // 0–1
 * @property {string|null} stage
 * @property {string|null} stage_label
 * @property {number|null} elapsed_ms
 * @property {string|null} error
 * @property {'service_restart'|'error'|null} [failure_kind]  see Job
 * @property {string} created_at        // ISO-8601
 * @property {string|null} completed_at
 * @property {MediaResult|null} result
 * @property {Object} meta              // model, prompt, provider, external_request_id, etc.
 */

/**
 * @typedef {Object} MediaResult
 * @property {'image'|'video'} type
 * @property {Array<{url: string, content_type?: string, width?: number, height?: number}>} [images]
 * @property {{url: string, content_type?: string}} [video]
 * @property {string} [provider]        // 'aihubmix' | 'pollinations' | 'higgsfield'
 * @property {string} [model]
 */

/**
 * @typedef {Object} MediaGenerateParams
 * @property {string} prompt
 * @property {string} [model]           // e.g. 'gpt-image-2-free' | 'higgsfield-ai/soul/v2/standard'
 * @property {'auto'|'image'|'video'} [kind]
 * @property {Object} [options]         // size, quality, aspect_ratio, duration, etc.
 * @property {string} [webhook_base]    // internal only; backend builds full URL
 */

/* ------------------------------------------------------------------ */
/* Admin console — operations surface, admin role only                */
/* ------------------------------------------------------------------ */

/**
 * Headline counters for the admin overview strip. Every value is a
 * measured figure the service owns; the client never invents them.
 *
 * @typedef {Object} AdminOverviewStats
 * @property {number} organizations       total organizations on the platform
 * @property {number} active_scrape_jobs  jobs currently queued or running
 * @property {'operational'|'degraded'|'down'} system_health  rolled-up state
 * @property {number} api_error_rate      5xx share over the trailing window, %
 * @property {string} window_label        human label for the measured window
 */

/**
 * One row in the admin recent-jobs table. Distinct from a discovery Job:
 * this is the operator's cross-tenant view, so it carries the owning
 * organization and a flat record count rather than stage internals.
 *
 * @typedef {Object} AdminJobRow
 * @property {string} job_id
 * @property {string} organization
 * @property {string} query
 * @property {'queued'|'running'|'succeeded'|'failed'} status
 * @property {number} records
 * @property {number} duration_ms
 * @property {string} created_at
 */

/**
 * A monitored dependency in the system-health panel.
 *
 * @typedef {Object} AdminServiceHealth
 * @property {string} id
 * @property {string} name
 * @property {'success'|'warning'|'danger'} status
 * @property {string} detail          short human status line
 * @property {number|null} latency_ms last measured probe latency
 * @property {string} last_checked    ISO-8601 UTC of the last probe
 */

/**
 * @typedef {Object} AdminSystemHealth
 * @property {'operational'|'degraded'|'down'} state  rolled-up state
 * @property {AdminServiceHealth[]} services
 */

/**
 * @typedef {Object} ScoutLead
 * @property {string} id
 * @property {string} job_id
 * @property {string} platform
 * @property {string} handle
 * @property {string|null} name
 * @property {string|null} email
 * @property {string|null} phone
 * @property {string|null} website
 * @property {string|null} bio
 * @property {number} followers
 * @property {number} lead_score
 * @property {Record<string, any>} sources
 * @property {string} created_at
 */

/**
 * @typedef {Object} ScoutJob
 * @property {string} job_id
 * @property {'queued'|'running'|'succeeded'|'failed'} status
 * @property {string} stage
 * @property {string} stage_label
 * @property {number} stage_index
 * @property {number} stages_total
 * @property {string[]} logs
 * @property {number} leads_count
 * @property {number} elapsed_ms
 * @property {number} credits_used
 * @property {string|null} error_msg
 * @property {string} created_at
 * @property {string|null} completed_at
 */

/**
 * @typedef {Object} ScoutMapsLead
 * @property {string} id
 * @property {string} job_id
 * @property {string} title
 * @property {string|null} phone
 * @property {string|null} email
 * @property {string[]} emails_found
 * @property {string|null} website
 * @property {string|null} category
 * @property {string|null} address
 * @property {string|null} city
 * @property {number|null} rating
 * @property {number} reviews_count
 * @property {string|null} instagram
 * @property {string|null} facebook
 * @property {string|null} linkedin
 * @property {string|null} twitter
 * @property {Record<string, any>} socials
 * @property {string} created_at
 */

/**
 * @typedef {Object} ScoutMapsJob
 * @property {string} job_id
 * @property {string} keyword
 * @property {string} city
 * @property {number} depth
 * @property {'queued'|'running'|'succeeded'|'failed'} status
 * @property {string} stage
 * @property {string} stage_label
 * @property {number} stage_index
 * @property {number} stages_total
 * @property {string[]} logs
 * @property {number} results_count
 * @property {number} elapsed_ms
 * @property {number} credits_used
 * @property {string|null} error_msg
 * @property {string} created_at
 * @property {string|null} completed_at
 */

export {}

/**
 * ============================================================
 * SCOUT · LEAD GENERATION CONTRACTS (engine: scrapling_engine)
 * ============================================================
 * JSDoc typedefs only. Social/Atlas has its own contracts — these tables are
 * deliberately separate (LeadGenJob / LeadGenLead on the backend too).
 * Honesty rule: logs and counters are real worker output; leads are never
 * fabricated — empty fields stay empty with provenance.
 * ============================================================
 */

/**
 * @typedef {Object} LeadGenBrief
 * @property {string} icp                      Required ideal-customer profile
 * @property {string[]} [geos]                 Default ["SA","AE","JO","EG"]
 * @property {string[]} [languages]
 * @property {string[]} [exclude_domains]
 * @property {number} [max_pages]              >= 1
 * @property {number} [max_leads]              >= 1
 * @property {number} [credit_budget]
 * @property {number} [outreach_min_score]     0..100, default 50
 */

/**
 * @typedef {Object} LeadGenSeeds
 * @property {string[]} [urls]                 Absolute http(s) URLs (validated/rejected server-side)
 * @property {string|null} [sitemap_url]
 * @property {string|null} [shopify_url]
 * @property {string|null} [domains_csv]       Raw CSV/JSONL text of domains or URLs
 */

/**
 * @typedef {Object} LeadGenJob
 * @property {string} job_id
 * @property {'queued'|'running'|'paused'|'succeeded'|'failed'} status
 * @property {'brief'|'seed'|'discover'|'fetch'|'extract'|'enrich'|'score'|'outreach'|'export'} stage
 * @property {string} stage_label
 * @property {number} stage_index
 * @property {number} stages_total             Always 9
 * @property {string[]} logs                   Canonical "> stage · detail" lines (tail persisted)
 * @property {number} leads_count
 * @property {number} pages_fetched
 * @property {number} pages_blocked
 * @property {number} elapsed_ms
 * @property {number} credits_used
 * @property {boolean} robots_obey             Default true; false writes an audit log line
 * @property {string} engine_default           http | stealth | dynamic
 * @property {string} mode                     crawl | sitemap | shopify | csv_feed | digest
 * @property {string|null} [recipe_id]
 * @property {string|null} [error_msg]
 * @property {string|null} [created_at]
 */

/**
 * @typedef {Object} LeadGenLead
 * @property {string} id
 * @property {string} job_id
 * @property {string|null} company_name
 * @property {string|null} website
 * @property {string|null} domain
 * @property {string[]} emails                 Empty stays empty — never fabricated
 * @property {string[]} phones
 * @property {Record<string,string>} socials
 * @property {string|null} address
 * @property {any[]} decision_makers
 * @property {string|null} markdown_excerpt
 * @property {string|null} markdown_artifact_path
 * @property {'empty'|'partial'|'ok'|'failed'} extract_status
 * @property {'ok'|'blocked'|'rate_limited'|'error'} fetch_status
 * @property {string} engine_used
 * @property {'website'|'hunter'|'bio'|'none'} email_source
 * @property {'website'|'bio'|'none'} phone_source
 * @property {number} lead_score               0..100, deterministic formula
 * @property {string|null} priority            high | med | low
 * @property {{subject:string,body:string,dm:string,personalization_points:string[],reason?:string}|null} outreach
 *                                                                                   Draft only — never auto-sent
 * @property {Record<string,any>} sources      Provenance: urls, selector hits, score breakdown
 * @property {string|null} [created_at]
 */

/**
 * @typedef {Object} LeadGenWorkerHealth
 * @property {'online'|'offline'} worker       Truthful: fresh heartbeat or URL ping required for online
 * @property {string|null} scrapling_version
 * @property {string[]} engines
 * @property {boolean} browsers_ready
 * @property {'configured'|'off'} proxy
 * @property {boolean} robots_default          robots_txt_obey default (true)
 * @property {string} [engine_default]
 * @property {number} queue_depth
 */
