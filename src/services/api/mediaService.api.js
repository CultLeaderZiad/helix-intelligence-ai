import { request } from "../http"

const mediaApi = {
  createJob: async (payload) => {
    return request("/media/jobs", { method: "POST", body: payload })
  },
  
  getJob: async (jobId) => {
    return request(`/media/jobs/${jobId}`, { method: "GET" })
  }
}

export default mediaApi
