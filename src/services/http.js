import { API_BASE_URL } from "./config"
import { getAccessToken } from "./sessionStore"

/**
 * Normalized service error. Both the mock and HTTP layers throw this,
 * so error-handling code in hooks never branches on data source.
 */
export class ServiceError extends Error {
  constructor(message, { status = null, code = "service_error" } = {}) {
    super(message)
    this.name = "ServiceError"
    this.status = status
    this.code = code
  }
}

function buildQuery(params = {}) {
  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue
    if (Array.isArray(value)) {
      if (value.length === 0) continue
      sp.set(key, value.join(","))
    } else if (typeof value === "object") {
      sp.set(key, JSON.stringify(value))
    } else {
      sp.set(key, String(value))
    }
  }
  const qs = sp.toString()
  return qs ? `?${qs}` : ""
}

function errorMessageFrom(detail, fallback) {
  if (typeof detail === "string" && detail.trim()) return detail
  if (Array.isArray(detail)) {
    for (const entry of detail) {
      const message = errorMessageFrom(entry, "")
      if (message) return message
    }
  } else if (detail && typeof detail === "object") {
    for (const key of ["message", "msg", "detail"]) {
      const message = errorMessageFrom(detail[key], "")
      if (message) return message
    }
  }
  return fallback
}

/**
 * Keep-alive & warm-up system:
 * Pings backend health in the background on startup and every 3 minutes
 * so all requests, logins, searches, and button clicks respond instantly with 0 delay.
 */
let isWarmedUp = false

export function getIsWarmedUp() {
  return isWarmedUp
}

// Ping immediately on startup and keep backend warm every 2 minutes
export function startBackendKeepAlive() {
  if (typeof window === "undefined") return
  
  const ping = async () => {
    try {
      await fetch(`${API_BASE_URL}/health`, { method: "GET", cache: "no-store" })
      isWarmedUp = true
    } catch {
      // Silent background ping
    }
  }

  // Ping immediately
  ping()
  // Keep warm every 2 minutes so Render backend never goes cold
  setInterval(ping, 2 * 60 * 1000)
}

// Start keepalive automatically on import in browser
startBackendKeepAlive()

/**
 * Core HTTP Request dispatcher with automatic resilient retries.
 * Automatically retries up to 6 times on transient network glitches or 502/503/504 errors
 * to gracefully absorb Render cold-start latency.
 */
export const HTTP_REQUEST_TIMEOUT_MS = 60000
const inFlightGetRequests = new Map()

function abortError(signal) {
  return signal?.reason || new DOMException("Request aborted", "AbortError")
}

function retryDelay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(abortError(signal)); return }
    const onAbort = () => {
      clearTimeout(timer)
      signal.removeEventListener("abort", onAbort)
      reject(abortError(signal))
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort)
      resolve()
    }, ms)
    signal?.addEventListener("abort", onAbort, { once: true })
  })
}

function normalizeTimeoutMs(options) {
  const requestedTimeout = options.timeoutMs ?? HTTP_REQUEST_TIMEOUT_MS
  return Number.isFinite(requestedTimeout) && requestedTimeout > 0
    ? Math.min(requestedTimeout, HTTP_REQUEST_TIMEOUT_MS) : HTTP_REQUEST_TIMEOUT_MS
}

function getInFlightGetKey(url, timeoutMs, sessionToken, headers) {
  const headerScope = Object.entries(headers || {})
    .map(([name, value]) => [name, String(value)])
    .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
  return JSON.stringify([sessionToken, url, timeoutMs, headerScope])
}

function startInFlightGet(key, path, options, sessionToken) {
  const controller = new AbortController()
  const entry = { key, controller, activeConsumers: 0, settled: false, promise: null }
  entry.promise = requestAttempt(path, { ...options, signal: controller.signal }, 0, sessionToken).then(
    value => {
      entry.settled = true
      if (inFlightGetRequests.get(key) === entry) inFlightGetRequests.delete(key)
      return value
    },
    error => {
      entry.settled = true
      if (inFlightGetRequests.get(key) === entry) inFlightGetRequests.delete(key)
      throw error
    },
  )
  inFlightGetRequests.set(key, entry)
  return entry
}

function waitForInFlightGet(entry, timeoutMs) {
  entry.activeConsumers += 1
  return new Promise((resolve, reject) => {
    let finished = false
    const timer = setTimeout(() => finish(false, new ServiceError("Request failed", { code: "request_timeout" })), timeoutMs)

    function finish(succeeded, value) {
      if (finished) return
      finished = true
      clearTimeout(timer)
      entry.activeConsumers -= 1
      if (entry.activeConsumers === 0 && !entry.settled) {
        if (inFlightGetRequests.get(entry.key) === entry) inFlightGetRequests.delete(entry.key)
        entry.controller.abort(new DOMException("Request aborted", "AbortError"))
      }
      if (succeeded) resolve(value)
      else reject(value)
    }

    entry.promise.then(value => finish(true, value), error => finish(false, error))
  })
}

/** One deadline covers fetches, response bodies and every retry delay. */
export async function request(path, options = {}) {
  const sessionToken = getAccessToken()
  const timeoutMs = normalizeTimeoutMs(options)
  const method = options.method || "GET"
  if (method.toUpperCase() === "GET" && !options.signal && !options.body) {
    const url = `${API_BASE_URL}${path}${buildQuery(options.params)}`
    const key = getInFlightGetKey(url, timeoutMs, sessionToken, options.headers)
    let entry = inFlightGetRequests.get(key)
    if (!entry || entry.settled || entry.controller.signal.aborted) {
      if (entry && inFlightGetRequests.get(key) === entry) inFlightGetRequests.delete(key)
      entry = startInFlightGet(key, path, options, sessionToken)
    }
    return waitForInFlightGet(entry, timeoutMs)
  }

  return requestWithDeadline(path, options, timeoutMs, sessionToken)
}

async function requestWithDeadline(path, options, timeoutMs, sessionToken) {
  const controller = new AbortController()
  const callerSignal = options.signal
  const onAbort = () => controller.abort(abortError(callerSignal))
  if (callerSignal?.aborted) onAbort()
  else callerSignal?.addEventListener("abort", onAbort, { once: true })
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort(new DOMException("Request aborted", "AbortError"))
  }, timeoutMs)
  try {
    return await requestAttempt(path, { ...options, signal: controller.signal })
  } catch (err) {
    if (timedOut) throw new ServiceError("Request failed", { code: "request_timeout" })
    throw err
  } finally {
    clearTimeout(timer)
    callerSignal?.removeEventListener("abort", onAbort)
  }
}

async function requestAttempt(path, options, retryCount = 0, sessionToken = getAccessToken()) {
  const { method = "GET", params, body, signal, headers: extraHeaders } = options
  if (signal.aborted) throw abortError(signal)
  const url = `${API_BASE_URL}${path}${buildQuery(params)}`

  const authHeader = sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}

  const upperMethod = (method || "GET").toUpperCase()
  const isIdempotentMethod = upperMethod === "GET" || upperMethod === "HEAD" || upperMethod === "OPTIONS"
  const hasIdempotencyKey = Boolean(
    extraHeaders && (
      extraHeaders["Idempotency-Key"] ||
      extraHeaders["idempotency-key"] ||
      extraHeaders["X-Idempotency-Key"] ||
      extraHeaders["x-idempotency-key"]
    )
  )
  const isSafeToRetry = isIdempotentMethod || hasIdempotencyKey

  let res
  try {
    res = await fetch(url, {
      method,
      signal,
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...authHeader,
        ...extraHeaders,
      },
      ...(body && typeof body !== "string" ? { body: JSON.stringify(body) } : body ? { body } : {}),
    })
  // Transparent retry on network disconnect / Render waking up (only for idempotent or key-protected requests)
  } catch (err) {
    if (signal.aborted) throw abortError(signal)
    if (err?.name === "AbortError") throw err

    if (isSafeToRetry && retryCount < 6) {
      const delay = Math.min(3500, 1000 * Math.pow(1.3, retryCount))
      await retryDelay(delay, signal)
      return requestAttempt(path, options, retryCount + 1, sessionToken)
    }

    throw new ServiceError(
      isSafeToRetry
        ? "Network connection interrupted. The server may be waking up."
        : "Network connection interrupted during request. To prevent duplicate charges, this operation was not automatically retried.",
      { code: "network_error" }
    )
  }

  // If server returns 502, 503, or 504 gateway error (Render cold-start boot), retry transparently only if safe
  // Do NOT retry structured JSON error responses (e.g. worker_offline 503) (F57)
  if (signal.aborted) throw abortError(signal)
  const isJsonError = res.headers?.get("content-type")?.includes("application/json")
  if (isSafeToRetry && [502, 503, 504].includes(res.status) && !isJsonError && retryCount < 8) {
    const delay = Math.min(4000, 1200 * Math.pow(1.3, retryCount))
    await retryDelay(delay, signal)
    return requestAttempt(path, options, retryCount + 1, sessionToken)
  }

  if (!res.ok) {
    let detail = res.statusText
    let errorCode = `http_${res.status}`
    try {
      const payload = await res.json()
      detail = payload?.detail ?? payload?.message ?? detail
      if (detail && typeof detail === "object" && !Array.isArray(detail)) {
        const structuredDetail = /** @type {{ code?: string }} */ (detail)
        if (typeof structuredDetail.code === "string") errorCode = structuredDetail.code
      }
    } catch {
      /* non-JSON error body */
    }
    detail = errorMessageFrom(detail, res.status === 422 ? "Validation error" : "Request failed")
    if (signal.aborted) throw abortError(signal)

    if (typeof detail === "string") {
      detail = detail.replace(/^(Value error,?\s*|String should have at least\s*)/i, "")
      if (detail.toLowerCase().includes("password must be at least 8 characters")) {
        detail = "Password must be at least 8 characters long."
      }
    }

    // F57: Only fall back to server_waking if the error was an unstructured gateway error
    if ([502, 503, 504].includes(res.status)) {
      if (!isJsonError || (errorCode === `http_${res.status}` && (detail === res.statusText || !detail))) {
        detail = "The backend server is waking up. Please click retry in a moment."
        errorCode = "server_waking"
      }
    }

    // Only dispatch unauthorized event for non-auth endpoints!
    // Never trigger sign-out while the user is actively on sign-in, sign-up, or session checks!
    const isAuthRoute = path.startsWith("/auth/") || path === "/auth"
    if (res.status === 401 && !isAuthRoute && getAccessToken() === sessionToken) {
      window.dispatchEvent(new CustomEvent("helix:unauthorized"))
    }

    throw new ServiceError(
      detail,
      { status: res.status, code: errorCode },
    )
  }

  if (res.status === 204) return null
  return res.json()
}


export async function uploadFile(path, formData, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const token = getAccessToken()
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {}

  let res
  try {
    res = await fetch(url, {
      method: "POST",
      signal: options.signal,
      headers: {
        Accept: "application/json",
        ...authHeader,
        ...options.headers,
      },
      body: formData,
    })
  } catch (err) {
    if (err?.name === "AbortError") throw err
    throw new ServiceError("Upload connection failed. Please try again.", { code: "network_error" })
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const payload = await res.json()
      detail = payload?.detail ?? payload?.message ?? detail
    } catch {}
    const isAuthRoute = path.startsWith("/auth/") || path === "/auth"
    if (res.status === 401 && !isAuthRoute && getAccessToken() === token) {
      window.dispatchEvent(new CustomEvent("helix:unauthorized"))
    }
    throw new ServiceError(typeof detail === "string" ? detail : "Upload failed", { status: res.status })
  }

  return res.json()
}
