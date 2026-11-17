import { request } from "../http"

/** Boards (saved-ad collections) and their guest links. */
const boardService = {
  listBoards() {
    return request("/boards")
  },

  /** @param {string} [collection] */
  listShareLinks(collection) {
    return request("/boards/share-links", { params: collection ? { collection } : {} })
  },

  /** @param {{collection: string, expires_in_days: number}} body */
  createShareLink(body) {
    return request("/boards/share-links", { method: "POST", body })
  },

  /** @param {string} linkId */
  revokeShareLink(linkId) {
    return request(`/boards/share-links/${encodeURIComponent(linkId)}`, { method: "DELETE" })
  },

  listTeamBoards() {
    return request("/boards/team")
  },

  /** @param {string} ownerId @param {string} collection */
  getTeamBoard(ownerId, collection) {
    return request("/boards/team/items", { params: { owner_id: ownerId, collection } })
  },

  /** W9-2: the caller's tags with counts. */
  listTags() {
    return request("/boards/tags")
  },

  /** Replace the tags on one saved ad. @param {string} creativeId @param {string[]} tags */
  setTags(creativeId, tags) {
    return request(`/boards/saved/${encodeURIComponent(creativeId)}/tags`, { method: "PUT", body: { tags } })
  },

  /** @param {string} creativeId @param {string} body */
  addNote(creativeId, body) {
    return request(`/boards/saved/${encodeURIComponent(creativeId)}/notes`, { method: "POST", body: { body } })
  },

  /** @param {string} creativeId @param {string} noteId @param {string} body */
  updateNote(creativeId, noteId, body) {
    return request(`/boards/saved/${encodeURIComponent(creativeId)}/notes/${encodeURIComponent(noteId)}`, { method: "PATCH", body: { body } })
  },

  /** @param {string} creativeId @param {string} noteId */
  deleteNote(creativeId, noteId) {
    return request(`/boards/saved/${encodeURIComponent(creativeId)}/notes/${encodeURIComponent(noteId)}`, { method: "DELETE" })
  },

  /** Guest read: no sign-in needed; the token is the capability. @param {string} token */
  getGuestBoard(token) {
    return request(`/public/boards/${encodeURIComponent(token)}`)
  },
}

export default boardService
