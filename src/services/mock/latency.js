import { MOCK_LATENCY_MS, MOCK_FAILURE_RATE } from "../config"
import { ServiceError } from "../http"

/**
 * Mocks are deliberately asynchronous and deliberately fallible.
 * Building against instant, always-successful arrays produces a UI
 * that has never rendered a skeleton or an error state.
 */
export function delay(ms) {
  const [min, max] = MOCK_LATENCY_MS
  const wait = ms ?? min + Math.random() * (max - min)
  return new Promise((resolve) => setTimeout(resolve, wait))
}

export function maybeFail(message = "Upstream source unavailable") {
  if (MOCK_FAILURE_RATE > 0 && Math.random() < MOCK_FAILURE_RATE) {
    throw new ServiceError(message, { status: 503, code: "upstream_unavailable" })
  }
}

let counter = 0
export function makeId(prefix) {
  counter += 1
  const rand = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${rand}${counter.toString(36)}`
}
