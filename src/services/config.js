/**
 * API location and client polling limits.
 *
 * Local and preview builds use the same-origin API proxy. Unclassified
 * production-mode builds use production origin rules. There is no mock data
 * source: every service talks to the FastAPI backend.
 */

import { resolveApiBaseUrl } from "./origin.js"

const env = import.meta.env

export const API_BASE_URL = resolveApiBaseUrl(
  env.VITE_API_BASE_URL,
  env.VITE_ENVIRONMENT,
  env.PROD === true
)

/** How often the client polls a running job. */
export const JOB_POLL_INTERVAL_MS = 400

/**
 * Ceiling on how long the client polls one job before treating it as stalled.
 *
 * The server marks a job interrupted by a restart as failed within roughly two
 * minutes, so this is only a backstop for a job that is stuck in some way the
 * server has not noticed. It must stay comfortably above that window or the
 * client would give up before the real reason arrives.
 */
export const JOB_POLL_TIMEOUT_MS = 240000
