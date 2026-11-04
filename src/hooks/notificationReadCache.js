import { notificationService, updatesService } from "@/services"
import { getAccessToken } from "@/services/sessionStore"

const CACHE_TTL_MS = 10_000
const RESOURCES = ["notifications", "updates"]
const completedReads = new Map()
const readGenerations = new Map()
let cacheEpoch = 0
let activeToken = null
let sessionVersion = 0

function cacheKey(scope, resource) {
  return JSON.stringify([scope, resource])
}

function pruneExpiredReads(now) {
  for (const [key, entry] of completedReads) {
    if (entry.expiresAt <= now) completedReads.delete(key)
  }
}

function readCompleted(scope, resource, loader, force) {
  if (!scope) return Promise.resolve().then(loader)

  const now = Date.now()
  pruneExpiredReads(now)
  const key = cacheKey(scope, resource)
  const cached = completedReads.get(key)
  if (!force && cached && cached.expiresAt > now) return Promise.resolve(cached.value)

  const generation = (readGenerations.get(key) || 0) + 1
  readGenerations.set(key, generation)
  const requestEpoch = cacheEpoch

  return Promise.resolve().then(loader).then((value) => {
    if (requestEpoch === cacheEpoch && readGenerations.get(key) === generation) {
      completedReads.set(key, { value, expiresAt: Date.now() + CACHE_TTL_MS })
    }
    return value
  }, (error) => {
    if (requestEpoch === cacheEpoch && readGenerations.get(key) === generation) {
      completedReads.delete(key)
    }
    throw error
  })
}

export function getNotificationReadScope(user) {
  if (user?.id == null) return null
  let token
  try {
    token = getAccessToken()
  } catch {
    return null
  }
  if (!token) {
    if (activeToken !== null) {
      activeToken = null
      sessionVersion += 1
    }
    return null
  }
  if (activeToken !== token) {
    activeToken = token
    sessionVersion += 1
  }
  return JSON.stringify([
    sessionVersion,
    String(user.id),
    user.organization_id == null ? null : String(user.organization_id),
  ])
}

export function readNotificationSources(scope, { force = false } = {}) {
  return Promise.allSettled([
    readCompleted(scope, "notifications", () => notificationService.getNotifications(), force),
    readCompleted(scope, "updates", () => updatesService.getPublishedUpdates(), force),
  ])
}

export function invalidateNotificationReads(scope) {
  if (!scope) return
  for (const resource of RESOURCES) {
    const key = cacheKey(scope, resource)
    completedReads.delete(key)
    readGenerations.set(key, (readGenerations.get(key) || 0) + 1)
  }
}

export function clearNotificationReadCache() {
  cacheEpoch += 1
  activeToken = null
  sessionVersion += 1
  completedReads.clear()
  readGenerations.clear()
}

if (typeof window !== "undefined") {
  window.addEventListener("helix:session-clearing", clearNotificationReadCache)
  window.addEventListener("helix:unauthorized", clearNotificationReadCache)
}
