import { request } from "../http"

/** @typedef {{ signal?: AbortSignal }} RequestOptions */

export const mediaService = {
  /** @param {object} params
   * @param {RequestOptions} [options] */
  generate: async (params, { signal } = {}) => {
    const res = await request("/media/jobs", {
      method: "POST",
      signal,
      body: JSON.stringify(params),
    })
    return {
      ...res,
      job_id: res.id || res.job_id,
    }
  },
  
  /** @param {string} jobId
   * @param {RequestOptions} [options] */
  getJob: async (jobId, { signal } = {}) => {
    const job = await request(`/media/jobs/${jobId}`, { signal })
    // Normalize backend status 'completed' -> 'succeeded' for frontend consistency
    if (job.status === "completed") {
      job.status = "succeeded"
    }
    return {
      ...job,
      job_id: job.id || job.job_id,
    }
  },
  
  /** @param {string} jobId
   * @param {RequestOptions} [options] */
  getJobResult: async (jobId, { signal } = {}) => {
    const job = await request(`/media/jobs/${jobId}`, { signal })
    if (job.status !== "succeeded" && job.status !== "completed") {
      const error = Object.assign(new Error("Job is not completed yet"), { status: 400 })
      throw error
    }
    
    // Normalize backend result into MediaResult shape
    const url = job.result_url || ""
    const isVideo = url.endsWith(".mp4") || url.endsWith(".webm") || url.includes("video") || (job.parameters && job.parameters.kind === "video")
    
    return {
      type: isVideo ? "video" : "image",
      url: url,
      video: isVideo ? { url } : undefined,
      images: isVideo ? undefined : [{ url }],
      provider: job.provider,
    }
  },
  
  /** @param {string} jobId
   * @param {RequestOptions} [options] */
  cancel: async (jobId, { signal } = {}) => {
    return request(`/media/jobs/${jobId}/cancel`, { method: "POST", signal })
  }
}

export default mediaService
