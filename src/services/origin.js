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
  const normalized = Object.hasOwn(ENVIRONMENT_ALIASES, raw) ? ENVIRONMENT_ALIASES[raw] : null
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

export function resolveApiBaseUrl(value, environment = "", productionBuild = false) {
  const env = normalizeFrontendEnvironment(environment.trim() || (productionBuild ? "production" : "development"))
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
    if (base.includes("\\")) throw new Error("Invalid URL")
    url = new URL(base)
  } catch {
    throw new Error("VITE_API_BASE_URL must be a same-origin path or a permitted HTTP(S) URL.")
  }
  if (!/^https?:$/.test(url.protocol) || !url.hostname || url.username || url.password || url.search || url.hash) {
    throw new Error("VITE_API_BASE_URL must be a same-origin path or a permitted HTTP(S) URL.")
  }

  const loopback = isLoopbackHostname(url.hostname)
  // Deployed builds (production, and production-mode preview/staging builds
  // such as Vercel previews) live on a different origin from the API, so they
  // may use a public HTTPS API host. Local development and tests stay on
  // loopback hosts.
  const deployedBuild = env === "production" || (productionBuild === true && (env === "preview" || env === "staging"))
  if (!deployedBuild && !loopback) {
    throw new Error("VITE_API_BASE_URL must use a loopback host outside deployed builds.")
  }
  const dnsHost = /\.[a-z][a-z\d-]*\.?$/i.test(url.hostname)
  if (env === "production" && (loopback || !dnsHost || url.protocol !== "https:")) {
    throw new Error("VITE_API_BASE_URL must use a public HTTPS DNS host in production.")
  }
  if (deployedBuild && !loopback && (!dnsHost || url.protocol !== "https:")) {
    throw new Error("VITE_API_BASE_URL must use a public HTTPS DNS host in deployed builds.")
  }

  return base.replace(/\/+$/, "")
}
