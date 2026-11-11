import { isColdStartFailure } from "@/services/coldStart"

/**
 * Why an auth submit failed, for the form banner.
 * Only a real 401/403 is a credential error. Timeouts and gateway
 * responses stay on the waking / unavailable path.
 * @param {unknown} error
 * @returns {"credentials" | "locked" | "unavailable" | "other"}
 */
export function classifyAuthFailure(error) {
  const failure = error && typeof error === "object"
    ? /** @type {{ status?: number, code?: string }} */ (error)
    : {}
  if (failure.status === 401 || failure.status === 403) return "credentials"
  if (failure.status === 429) return "locked"
  if (failure.code === "server_unavailable" || isColdStartFailure(error)) return "unavailable"
  return "other"
}
