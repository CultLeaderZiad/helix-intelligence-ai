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

  /** Guest read: no sign-in needed; the token is the capability. @param {string} token */
  getGuestBoard(token) {
    return request(`/public/boards/${encodeURIComponent(token)}`)
  },
}

export default boardService
