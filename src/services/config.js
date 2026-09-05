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

/** @type {'mock'|'api'} */
export const DATA_SOURCE = env.VITE_DATA_SOURCE === "api" ? "api" : "mock"

export const API_BASE_URL = env.VITE_API_BASE_URL ?? "/api"

/** Mock-only knobs, used to rehearse slow networks and failures. */
export const MOCK_LATENCY_MS = [180, 520]
export const MOCK_FAILURE_RATE = Number(env.VITE_MOCK_FAILURE_RATE ?? 0)

/** How often the client polls a running job. */
export const JOB_POLL_INTERVAL_MS = 400

/** Ceiling on how long the client polls one job before treating it as
 *  stalled (server jobs normally finish in seconds; minutes means dead). */
export const JOB_POLL_TIMEOUT_MS = 240000
