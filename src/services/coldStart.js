import { API_BASE_URL } from "./config"

/** How long sign-in and sign-up will wait for the free Render service to answer /api/health. */
export const HEALTH_WAIT_BUDGET_MS = 90_000

/**
 * @typedef {(input: string, init?: RequestInit) => Promise<{ ok?: boolean, status?: number }>} HealthFetch
 */

/**
 * @typedef {{
 *   healthUrl?: string,
 *   budgetMs?: number,
 *   initialDelayMs?: number,
 *   maxDelayMs?: number,
 *   attemptTimeoutMs?: number,
 *   fetchImpl?: HealthFetch,
 *   sleep?: (ms: number) => Promise<void>,
 *   now?: () => number,
 *   createUnavailableError?: () => Error,
 * }} ColdStartOptions
 */

/**
 * A transport failure while the free instance is asleep.
 * Credential refusals (401/403) are not cold starts.
 * @param {unknown} error
 */
export function isColdStartFailure(error) {
  if (!error || typeof error !== "object") return false
  const failure = /** @type {{ code?: string, status?: number, name?: string }} */ (error)
  if (failure.name === "AbortError") return false
  if (
    failure.code === "network_error" ||
    failure.code === "request_timeout" ||
    failure.code === "server_waking"
  ) {
    return true
  }
  return failure.status === 502 || failure.status === 503 || failure.status === 504
}

/**
 * @param {number} ms
 * @returns {Promise<void>}
 */
function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

/**
 * @param {string} url
 * @param {HealthFetch} fetchImpl
 * @param {number} timeoutMs
 */
async function probeHealth(url, fetchImpl, timeoutMs) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), Math.max(1, timeoutMs))
  try {
    const response = await fetchImpl(url, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    })
    return response?.ok === true && response.status === 200
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Poll GET /api/health with exponential backoff until it returns 200 or the budget is spent.
 * The first probe runs immediately.
 * @param {ColdStartOptions} [options]
 * @returns {Promise<boolean>}
 */
export async function waitUntilHealthy(options = {}) {
  const budgetMs = options.budgetMs ?? HEALTH_WAIT_BUDGET_MS
  const healthUrl = options.healthUrl ?? `${API_BASE_URL}/health`
  const fetchImpl = options.fetchImpl ?? /** @type {HealthFetch} */ (globalThis.fetch.bind(globalThis))
  const sleep = options.sleep ?? delay
  const now = options.now ?? Date.now
  const maxDelayMs = options.maxDelayMs ?? 8000
  const attemptTimeoutMs = options.attemptTimeoutMs ?? 15_000
  const started = now()
  let delayMs = options.initialDelayMs ?? 1000

  while (now() - started < budgetMs) {
    const remaining = budgetMs - (now() - started)
    if (remaining <= 0) return false
    const healthy = await probeHealth(healthUrl, fetchImpl, Math.min(attemptTimeoutMs, remaining))
    if (healthy) return true
    const afterProbe = budgetMs - (now() - started)
    if (afterProbe <= 0) return false
    await sleep(Math.min(delayMs, afterProbe))
    delayMs = Math.min(maxDelayMs, delayMs * 2)
  }
  return false
}

/**
 * @param {ColdStartOptions} options
 */
function unavailableError(options) {
  if (typeof options.createUnavailableError === "function") {
    return options.createUnavailableError()
  }
  const error = /** @type {Error & { code: string, status: null }} */ (
    new Error("The server is unavailable. Try again in a moment.")
  )
  error.name = "ServiceError"
  error.code = "server_unavailable"
  error.status = null
  return error
}

/**
 * Run an auth write once. On a timeout or gateway error, wait until health
 * is 200 and run it one more time. The second call starts only after the
 * first promise has settled, so the two requests are never in flight together.
 * @template T
 * @param {() => Promise<T>} operation
 * @param {ColdStartOptions} [options]
 * @returns {Promise<T>}
 */
export async function withColdStartRetry(operation, options = {}) {
  try {
    return await operation()
  } catch (error) {
    if (!isColdStartFailure(error)) throw error
    const healthy = await waitUntilHealthy(options)
    if (!healthy) throw unavailableError(options)
    try {
      return await operation()
    } catch (retryError) {
      if (isColdStartFailure(retryError)) throw unavailableError(options)
      throw retryError
    }
  }
}
