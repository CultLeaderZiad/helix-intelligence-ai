const ENVIRONMENT_ALIASES = {
  production: "production",
  prod: "production",
  staging: "staging",
  stage: "staging",
  preview: "preview",
  test: "test",
  testing: "test",
  development: "development",
  dev: "development",
  local: "development",
}

export function normalizeFrontendEnvironment(value) {
  const raw = (value ?? "").trim().toLowerCase()
  if (!raw) return "development"
  const normalized = ENVIRONMENT_ALIASES[raw]
  if (!normalized) {
    throw new Error("VITE_ENVIRONMENT must identify a recognized deployment environment.")
  }
  return normalized
}

function isLoopbackHostname(hostname) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "")
  if (host === "localhost" || host.endsWith(".localhost") || host === "::1") return true
  const octets = host.split(".").map(Number)
  return octets.length === 4 && octets[0] === 127 && octets.every((part) => part >= 0 && part <= 255)
}

export function resolveApiBaseUrl(value, environment = "development", productionBuild = false) {
  const env = normalizeFrontendEnvironment(environment)
  if (env === "production" && productionBuild !== true) {
    throw new Error("VITE_ENVIRONMENT=production requires a production build.")
  }

  const base = typeof value === "string" && value.trim() ? value.trim() : "/api"
  if (base.startsWith("/")) {
    if (base.startsWith("//") || base.includes("\\") || base.includes("?") || base.includes("#")) {
      throw new Error("VITE_API_BASE_URL must be a same-origin path or a permitted HTTP(S) URL.")
    }
    return base.replace(/\/+$/, "") || "/"
  }

  let url
  try {
    url = new URL(base)
  } catch {
    throw new Error("VITE_API_BASE_URL must be a same-origin path or a permitted HTTP(S) URL.")
  }
  if (!/^https?:$/.test(url.protocol) || !url.hostname || url.username || url.password || url.search || url.hash) {
    throw new Error("VITE_API_BASE_URL must be a same-origin path or a permitted HTTP(S) URL.")
  }

  const loopback = isLoopbackHostname(url.hostname)
  if (env !== "production" && !loopback) {
    throw new Error("VITE_API_BASE_URL must use a loopback host outside production.")
  }
  if (env === "production" && (loopback || url.protocol !== "https:")) {
    throw new Error("VITE_API_BASE_URL must use a public HTTPS host in production.")
  }

  return base.replace(/\/+$/, "")
}
