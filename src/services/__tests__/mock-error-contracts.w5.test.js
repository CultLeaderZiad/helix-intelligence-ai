import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { ServiceError } from "../http"
import mediaService from "../mock/mediaService.mock"

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it.each(["getJob", "getJobResult"])("%s preserves the missing-job status", async method => {
  const pending = mediaService[method]("missing-job").catch(error => error)
  await vi.runAllTimersAsync()
  const error = await pending
  expect(error).toBeInstanceOf(ServiceError)
  expect(error.status).toBe(404)
})
