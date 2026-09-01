import { request } from "../http"

export const dashboardApi = {
  getMetrics: async () => {
    return await request("/dashboard/metrics")
  }
}

export default dashboardApi
