/**
 * One browser session store.
 *
 * The access token and cached profile live only in localStorage. Older builds
 * also wrote the same token to sessionStorage; reads migrate that copy once
 * and then delete it so the two stores cannot disagree.
 *
 * An HttpOnly cookie move still needs CSRF, CORS, and external-issuer tests.
 */

const TOKEN_KEY = "helix_access_token"
const USER_KEY = "helix_cached_user"
const LEGACY_TOKEN_KEYS = ["helix_auth_token", "helix_admin_token"]

function hasWindow() {
  return typeof window !== "undefined"
}

function readStore(store, key) {
  try {
    return store.getItem(key)
  } catch {
    return null
  }
}

function writeStore(store, key, value) {
  try {
    store.setItem(key, value)
  } catch {
    /* storage can be blocked */
  }
}

function dropStore(store, key) {
  try {
    store.removeItem(key)
  } catch {
    /* storage can be blocked */
  }
}

function local() {
  if (!hasWindow()) return null
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function session() {
  if (!hasWindow()) return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function forgetDuplicates(keepToken) {
  const persistent = local()
  const tab = session()
  for (const key of [TOKEN_KEY, USER_KEY, ...LEGACY_TOKEN_KEYS]) {
    if (tab) dropStore(tab, key)
    if (persistent && key !== TOKEN_KEY && key !== USER_KEY) dropStore(persistent, key)
  }
  if (!keepToken && persistent) dropStore(persistent, TOKEN_KEY)
}

export function getAccessToken() {
  const persistent = local()
  if (!persistent) return null
  const current = readStore(persistent, TOKEN_KEY)
  if (current) {
    const tab = session()
    if (tab) {
      dropStore(tab, TOKEN_KEY)
      for (const key of LEGACY_TOKEN_KEYS) dropStore(tab, key)
    }
    for (const key of LEGACY_TOKEN_KEYS) dropStore(persistent, key)
    return current
  }
  const tab = session()
  const migrated =
    (tab && (readStore(tab, TOKEN_KEY) || LEGACY_TOKEN_KEYS.map((key) => readStore(tab, key)).find(Boolean))) ||
    LEGACY_TOKEN_KEYS.map((key) => readStore(persistent, key)).find(Boolean) ||
    null
  if (!migrated) return null
  writeStore(persistent, TOKEN_KEY, migrated)
  forgetDuplicates(true)
  return migrated
}

export function setAccessToken(token) {
  const persistent = local()
  if (!persistent || !token) {
    clearAccessToken()
    return
  }
  writeStore(persistent, TOKEN_KEY, token)
  forgetDuplicates(true)
}

export function clearAccessToken() {
  forgetDuplicates(false)
}

export function getCachedUser() {
  const persistent = local()
  if (!persistent) return null
  const raw = readStore(persistent, USER_KEY) || (session() && readStore(session(), USER_KEY))
  if (!raw) return null
  if (!readStore(persistent, USER_KEY)) writeStore(persistent, USER_KEY, raw)
  const tab = session()
  if (tab) dropStore(tab, USER_KEY)
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setCachedUser(user) {
  const persistent = local()
  if (!persistent || !user) return
  writeStore(persistent, USER_KEY, JSON.stringify(user))
  const tab = session()
  if (tab) dropStore(tab, USER_KEY)
}

export function clearCachedUser() {
  const persistent = local()
  const tab = session()
  if (persistent) dropStore(persistent, USER_KEY)
  if (tab) dropStore(tab, USER_KEY)
}

export function clearSession() {
  clearAccessToken()
  clearCachedUser()
  const persistent = local()
  const tab = session()
  const extra = [
    "helix_impersonation",
    "helix_impersonated_user",
    "helix_latest_search",
    "helix_search_history",
    "helix_active_creative",
    "helix_saved_drafts",
  ]
  for (const key of extra) {
    if (persistent) dropStore(persistent, key)
    if (tab) dropStore(tab, key)
  }
}
