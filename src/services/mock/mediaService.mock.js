import { delay } from "./latency"
import { ServiceError } from "../http"

const jobs = new Map()

export const mediaService = {
  generate: async (params) => {
    await delay(300)
    const jobId = crypto.randomUUID()
    const now = new Date().toISOString()
    
    const job = {
      job_id: jobId,
      status: "queued",
      progress: 0,
      stage: "initializing",
      stage_label: "Initializing generation...",
      elapsed_ms: 0,
      created_at: now,
      completed_at: null,
      result: null,
      meta: {
        prompt: params.prompt,
        model: params.model || "mock-model",
        provider: "mock"
      }
    }
    
    jobs.set(jobId, job)
    
    // Simulate background progress
    setTimeout(() => {
      const activeJob = jobs.get(jobId)
      if (activeJob && activeJob.status === "queued") {
        activeJob.status = "running"
        activeJob.progress = 0.2
        activeJob.stage_label = "Generating layout..."
      }
    }, 1500)
    
    setTimeout(() => {
      const activeJob = jobs.get(jobId)
      if (activeJob && activeJob.status === "running") {
        activeJob.progress = 0.6
        activeJob.stage_label = "Refining details..."
      }
    }, 3500)
    
    setTimeout(() => {
      const activeJob = jobs.get(jobId)
      if (activeJob && activeJob.status === "running") {
        activeJob.status = "succeeded"
        activeJob.progress = 1.0
        activeJob.stage_label = "Completed"
        activeJob.completed_at = new Date().toISOString()
        activeJob.result = {
          type: "image",
          images: [{ url: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=800&q=80", content_type: "image/jpeg" }],
          provider: "mock",
          model: activeJob.meta.model
        }
      }
    }, 5000)
    
    return job
  },
  
  getJob: async (jobId) => {
    await delay(150)
    const job = jobs.get(jobId)
    if (!job) throw new ServiceError("Job not found", 404)
    return { ...job } // return a copy to prevent mutation bugs
  },
  
  getJobResult: async (jobId) => {
    await delay(100)
    const job = jobs.get(jobId)
    if (!job) throw new ServiceError("Job not found", 404)
    if (job.status !== "succeeded") {
      throw new ServiceError("Job is not completed yet", 400)
    }
    return job.result
  },
  
  cancel: async (jobId) => {
    await delay(100)
    const job = jobs.get(jobId)
    if (job && (job.status === "queued" || job.status === "running")) {
      job.status = "canceled"
      job.completed_at = new Date().toISOString()
    }
  }
}

export default mediaService
