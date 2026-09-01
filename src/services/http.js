import { API_BASE_URL } from "./config"

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

/**
 * Keep-alive & warm-up system:
 * Pings backend health in the background on startup and every 3 minutes
 * so all requests, logins, searches, and button clicks respond instantly with 0 delay.
 */
let isWarmedUp = false
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
  // Keep warm every 3 minutes
  setInterval(ping, 3 * 60 * 1000)
}

// Start keepalive automatically on import in browser
startBackendKeepAlive()

/**
 * Core HTTP Request dispatcher with automatic resilient retries.
 * Automatically retries up to 2 times on transient network glitches or 502/503/504 errors.
 */
export async function request(path, options = {}, retryCount = 0) {
  const { method = "GET", params, body, signal, headers: extraHeaders } = options
  const url = `${API_BASE_URL}${path}${buildQuery(params)}`

  // Attach JWT from localStorage if present
  const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token")
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {}

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
  } catch (err) {
    if (err?.name === "AbortError") throw err

    // Transparent fast retry on network disconnect / connection drop (max 2 retries)
    if (retryCount < 2 && method === "GET") {
      await new Promise((resolve) => setTimeout(resolve, 300 * (retryCount + 1)))
      return request(path, options, retryCount + 1)
    }

    throw new ServiceError("Network connection interrupted. Please try again.", { code: "network_error" })
  }

  // If server returns 502, 503, or 504 gateway error, retry transparently
  if ([502, 503, 504].includes(res.status) && retryCount < 2) {
    await new Promise((resolve) => setTimeout(resolve, 500 * (retryCount + 1)))
    return request(path, options, retryCount + 1)
  }

  if (!res.ok) {
    let detail = res.statusText
    let errorCode = `http_${res.status}`
    try {
      const payload = await res.json()
      detail = payload?.detail ?? payload?.message ?? detail
      if (Array.isArray(detail) && detail.length > 0) {
        detail = detail[0].msg || "Validation error"
      } else if (typeof detail === "object" && detail !== null) {
        if (detail.code) errorCode = detail.code
        if (detail.message) detail = detail.message
      }
    } catch {
      /* non-JSON error body */
    }

    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent("helix:unauthorized"))
    }

    throw new ServiceError(
      typeof detail === "string" ? detail : "Request failed",
      { status: res.status, code: errorCode },
    )
  }

  if (res.status === 204) return null
  return res.json()
}

export async function uploadFile(path, formData, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token")
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {}

  let res
  try {
    res = await fetch(url, {
      method: "POST",
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
    throw new ServiceError(typeof detail === "string" ? detail : "Upload failed", { status: res.status })
  }

  return res.json()
}
