import { isColdStartFailure } from "@/services/coldStart"

/**
 * Why an auth submit failed, for the form banner.
 * Only a real 401/403 is a credential error. Timeouts and gateway
 * responses stay on the waking / unavailable path.
 * @param {unknown} error
 * A 429 with code "rate_limited" is a request limit (wait and retry);
 * any other 429 is the per-account sign-in lock.
 * @returns {"credentials" | "locked" | "rate_limited" | "unavailable" | "other"}
 */
export function classifyAuthFailure(error) {
  const failure = error && typeof error === "object"
    ? /** @type {{ status?: number, code?: string }} */ (error)
    : {}
  if (failure.status === 401 || failure.status === 403) return "credentials"
  if (failure.status === 429) return failure.code === "rate_limited" ? "rate_limited" : "locked"
  if (failure.code === "server_unavailable" || isColdStartFailure(error)) return "unavailable"
  return "other"
}
