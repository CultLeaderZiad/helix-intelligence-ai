import { request } from "../http"

const agentService = {
  limits() {
    return request("/agent/limits")
  },

  /**
   * @param {string} question
   * @param {{ role: string, content: string }[]} history
   * @param {string} lang
   * @param {{ references?: { type: string, id: string }[], effort?: string, signal?: AbortSignal }} [options]
   */
  ask(question, history, lang, options = {}) {
    const { references = [], effort = "think", signal, conversationId } = options
    return request("/agent/ask", {
      method: "POST",
      body: { question, history, lang, effort, model: "cyreax-z1", references: references.map(({ type, id }) => ({ type, id })), conversation_id: conversationId || undefined },
      timeoutMs: 90000,
      signal,
    })
  },

  /** Saved conversations (private to the caller). @param {boolean} [archived] */
  conversations(archived = false) {
    return request("/agent/conversations", { params: { archived } })
  },

  /** One conversation with its messages. @param {string} id */
  conversation(id) {
    return request(`/agent/conversations/${encodeURIComponent(id)}`)
  },

  /** @param {string} id @param {{ title?: string, pinned?: boolean, archived?: boolean }} body */
  updateConversation(id, body) {
    return request(`/agent/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body })
  },

  /** @param {string} id */
  deleteConversation(id) {
    return request(`/agent/conversations/${encodeURIComponent(id)}`, { method: "DELETE" })
  },

  /** What the "@" menu offers: the caller's own searches, drafts, boards and monitors. */
  mentions(q = "", signal) {
    return request("/agent/mentions", { params: { q, limit: 20 }, signal })
  },

  generate({ creativeId, product, language, dialect }) {
    return request("/agent/generate", {
      method: "POST",
      body: { creative_id: creativeId, product, language, dialect: language === "ar" ? dialect : null },
      timeoutMs: 90000,
    })
  },

  /** Run an approved proposal through its normal, already-authorised endpoint. */
  async approve(proposal) {
    const steps = proposal.requests || [proposal.request]
    const results = []
    for (const step of steps) {
      results.push(await request(step.path, { method: step.method, body: step.body, params: step.params, timeoutMs: 90000 }))
    }
    return results
  },
}

export default agentService
