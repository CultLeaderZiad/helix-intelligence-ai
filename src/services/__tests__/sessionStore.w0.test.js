import assert from "node:assert/strict"
import test from "node:test"

function memoryStore() {
  const values = new Map()
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    },
  }
}

globalThis.window = globalThis
globalThis.localStorage = memoryStore()
globalThis.sessionStorage = memoryStore()

const session = await import("../sessionStore.js")

test("setAccessToken writes one localStorage key and clears sessionStorage", () => {
  sessionStorage.setItem("helix_access_token", "stale-session")
  localStorage.setItem("helix_auth_token", "stale-legacy")
  session.setAccessToken("fresh-token")
  assert.equal(localStorage.getItem("helix_access_token"), "fresh-token")
  assert.equal(sessionStorage.getItem("helix_access_token"), null)
  assert.equal(localStorage.getItem("helix_auth_token"), null)
  assert.equal(session.getAccessToken(), "fresh-token")
})

test("getAccessToken migrates a sessionStorage token once", () => {
  localStorage.removeItem("helix_access_token")
  sessionStorage.setItem("helix_access_token", "moved-token")
  assert.equal(session.getAccessToken(), "moved-token")
  assert.equal(localStorage.getItem("helix_access_token"), "moved-token")
  assert.equal(sessionStorage.getItem("helix_access_token"), null)
})

test("clearSession removes both stores", () => {
  session.setAccessToken("fresh-token")
  session.setCachedUser({ id: "user-1" })
  sessionStorage.setItem("helix_cached_user", "{\"id\":\"old\"}")
  session.clearSession()
  assert.equal(session.getAccessToken(), null)
  assert.equal(session.getCachedUser(), null)
  assert.equal(localStorage.getItem("helix_cached_user"), null)
  assert.equal(sessionStorage.getItem("helix_cached_user"), null)
})
