import { request } from "../http"

export const dashboardApi = {
  getMetrics: async () => {
    return await request("/api/v1/dashboard/metrics")
  }
}

export default dashboardApi
