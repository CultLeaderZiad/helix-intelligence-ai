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
 * The only place in the client that knows about fetch, base URLs,
 * auth headers or error normalization. Auth, retries and cancellation
 * all land here — not in features.
 *
 * @param {string} path
 * @param {{ method?: string, params?: Object, body?: any, signal?: AbortSignal }} [options]
 */
export async function request(path, options = {}) {
  const { method = "GET", params, body, signal } = options
  const url = `${API_BASE_URL}${path}${buildQuery(params)}`

  let res
  try {
    res = await fetch(url, {
      method,
      signal,
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
  } catch (err) {
    if (err?.name === "AbortError") throw err
    throw new ServiceError("Network request failed", { code: "network_error" })
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const payload = await res.json()
      // FastAPI conventionally returns { detail: ... }
      detail = payload?.detail ?? payload?.message ?? detail
    } catch {
      /* non-JSON error body */
    }
    throw new ServiceError(
      typeof detail === "string" ? detail : "Request failed",
      { status: res.status, code: `http_${res.status}` },
    )
  }

  if (res.status === 204) return null
  return res.json()
}
