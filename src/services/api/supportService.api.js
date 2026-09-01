import { request } from "../http"

/**
 * Support and Feedback tickets API service.
 * Handles ticket creation, threaded replies, and list retrieval.
 */
const supportService = {
  createTicket(data) {
    return request("/support/tickets", {
      method: "POST",
      body: data,
    })
  },

  listTickets() {
    return request("/support/tickets")
  },

  getTicket(ticketId) {
    return request(`/support/tickets/${ticketId}`)
  },

  replyTicket(ticketId, message) {
    return request(`/support/tickets/${ticketId}/reply`, {
      method: "POST",
      body: { message },
    })
  },
}

export default supportService
