import { request } from "../http"

export const mediaService = {
  generate: async (params) => {
    return request("/media/jobs", {
      method: "POST",
      body: JSON.stringify(params),
    })
  },
  
  getJob: async (jobId) => {
    const job = await request(`/media/jobs/${jobId}`)
    // Normalize backend status 'completed' -> 'succeeded' for frontend consistency
    if (job.status === "completed") {
      job.status = "succeeded"
    }
    return job
  },
  
  getJobResult: async (jobId) => {
    const job = await request(`/media/jobs/${jobId}`)
    if (job.status !== "succeeded" && job.status !== "completed") {
      const error = new Error("Job is not completed yet")
      error.status = 400
      throw error
    }
    
    // Normalize backend result into MediaResult shape
    return {
      type: "video", // Defaulting for Higgsfield, in a real app check backend response
      video: { url: job.result_url },
      provider: job.provider,
    }
  },
  
  cancel: async (jobId) => {
    return request(`/media/jobs/${jobId}/cancel`, { method: "POST" })
  }
}

export default mediaService
