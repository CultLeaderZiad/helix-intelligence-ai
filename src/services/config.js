/**
 * The single switch that decides where data comes from.
 *
 * Cutover to FastAPI is:
 *   VITE_DATA_SOURCE=api
 *   VITE_API_BASE_URL=https://api.helix.internal
 *
 * No component or hook changes. Nothing else in the app reads these vars.
 */

const env = import.meta.env ?? {}

const VALID_DATA_SOURCES = ["api", "mock"]
const rawDataSource = (env.VITE_DATA_SOURCE ?? "api").trim().toLowerCase()

if (!VALID_DATA_SOURCES.includes(rawDataSource)) {
  throw new Error(
    `Invalid VITE_DATA_SOURCE: '${env.VITE_DATA_SOURCE}'. Allowed values are 'api' or 'mock'.`
  )
}

if (env.PROD && rawDataSource === "mock") {
  throw new Error(
    "VITE_DATA_SOURCE cannot be set to 'mock' in production builds. Production must connect to real API backend."
  )
}

/** @type {'mock'|'api'} */
export const DATA_SOURCE = rawDataSource === "mock" ? "mock" : "api"

export const API_BASE_URL = env.VITE_API_BASE_URL ?? "/api"

/** Mock-only knobs, used to rehearse slow networks and failures. */
export const MOCK_LATENCY_MS = [180, 520]
export const MOCK_FAILURE_RATE = Number(env.VITE_MOCK_FAILURE_RATE ?? 0)

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
