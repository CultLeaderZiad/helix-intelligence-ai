import { request } from "../http"

const notificationService = {
  getNotifications() {
    return request("/notifications/")
  },

  markAsRead(notificationId) {
    return request(`/notifications/${notificationId}/read`, {
      method: "POST",
    })
  },

  markAllAsRead() {
    return request("/notifications/read-all", {
      method: "POST",
    })
  },
}

export default notificationService
