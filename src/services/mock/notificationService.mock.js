import { delay } from "./latency"

const notificationService = {
  async getNotifications() {
    await delay(100)
    return {
      items: [
        {
          id: "n_1",
          type: "info",
          title: "Welcome to Helix Intelligence",
          message: "Your 7-day free trial has been activated with 25 free credits.",
          is_read: false,
          created_at: new Date().toISOString()
        }
      ],
      unread_count: 1
    }
  },

  async markAsRead(id) {
    await delay(50)
    return { success: true }
  },

  async markAllAsRead() {
    await delay(50)
    return { success: true }
  }
}

export default notificationService
