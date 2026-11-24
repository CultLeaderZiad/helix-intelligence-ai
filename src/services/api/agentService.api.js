import { request } from "../http"

const agentService = {
  limits() {
    return request("/agent/limits")
  },

  ask(question, history, lang) {
    return request("/agent/ask", { method: "POST", body: { question, history, lang }, timeoutMs: 90000 })
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
