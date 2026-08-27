import { delay } from "./latency"

const mediaMock = {
  createJob: async (payload) => {
    await delay(800)
    return {
      id: "job-123",
      status: "pending",
      prompt: payload.prompt,
      provider: payload.provider,
      parameters: payload.parameters,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  },
  
  getJob: async (jobId) => {
    await delay(300)
    // Randomly transition to completed
    const isDone = Math.random() > 0.5
    return {
      id: jobId,
      status: isDone ? "completed" : "in_progress",
      prompt: "Mock prompt",
      provider: "mock",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      result_url: isDone ? "https://www.w3schools.com/html/mov_bbb.mp4" : null
    }
  }
}

export default mediaMock
