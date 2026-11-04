import { act, cleanup, render } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { NotificationBell } from "@/components/NotificationBell"
import { clearNotificationReadCache } from "@/hooks/notificationReadCache"
import { setAccessToken } from "@/services/sessionStore"

const serviceMocks = vi.hoisted(() => ({
  getNotifications: vi.fn(),
  markAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
  getPublishedUpdates: vi.fn(),
}))

vi.mock("@/services", () => ({
  notificationService: {
    getNotifications: serviceMocks.getNotifications,
    markAsRead: serviceMocks.markAsRead,
    markAllAsRead: serviceMocks.markAllAsRead,
  },
  updatesService: { getPublishedUpdates: serviceMocks.getPublishedUpdates },
}))

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "member-1", organization_id: "workspace-1" } }),
}))

vi.mock("@/context/LanguageContext", () => ({
  useLanguage: () => ({ lang: "en", t: (_key, fallback) => fallback || _key }),
}))

const originalVisibility = Object.getOwnPropertyDescriptor(document, "visibilityState")

function setVisibilityState(value) {
  Object.defineProperty(document, "visibilityState", { configurable: true, value })
}

function renderBell() {
  return render(
    <MemoryRouter>
      <NotificationBell className="" />
    </MemoryRouter>,
  )
}

async function flushPromises() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
  })
}

beforeEach(() => {
  window.localStorage.clear()
  clearNotificationReadCache()
  setAccessToken("bell-session")
  vi.clearAllMocks()
  serviceMocks.getNotifications.mockResolvedValue({ items: [] })
  serviceMocks.markAsRead.mockResolvedValue({ ok: true })
  serviceMocks.markAllAsRead.mockResolvedValue({ ok: true })
  serviceMocks.getPublishedUpdates.mockResolvedValue([])
  setVisibilityState("visible")
})

afterEach(() => {
  cleanup()
  vi.clearAllTimers()
  vi.useRealTimers()
  if (originalVisibility) {
    Object.defineProperty(document, "visibilityState", originalVisibility)
  } else {
    Reflect.deleteProperty(document, "visibilityState")
  }
})

describe("NotificationBell polling", () => {
  it("pauses while hidden, resumes on visibility, and ignores window focus", async () => {
    vi.useFakeTimers()
    setVisibilityState("hidden")
    renderBell()
    await flushPromises()
    expect(serviceMocks.getNotifications).not.toHaveBeenCalled()
    expect(serviceMocks.getPublishedUpdates).not.toHaveBeenCalled()

    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(serviceMocks.getNotifications).not.toHaveBeenCalled()

    setVisibilityState("visible")
    act(() => document.dispatchEvent(new Event("visibilitychange")))
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(1)
    expect(serviceMocks.getPublishedUpdates).toHaveBeenCalledTimes(1)

    clearNotificationReadCache()
    act(() => window.dispatchEvent(new Event("focus")))
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(2)

    setVisibilityState("hidden")
    act(() => document.dispatchEvent(new Event("visibilitychange")))
    await act(async () => { await vi.advanceTimersByTimeAsync(120_000) })
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(2)

    setVisibilityState("visible")
    act(() => document.dispatchEvent(new Event("visibilitychange")))
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(3)
    expect(serviceMocks.getPublishedUpdates).toHaveBeenCalledTimes(3)
  })

  it("backs off after failed reads instead of retrying on the normal interval", async () => {
    vi.useFakeTimers()
    serviceMocks.getNotifications.mockRejectedValueOnce(new Error("offline"))
    renderBell()
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(39_999) })
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    await flushPromises()
    expect(serviceMocks.getNotifications).toHaveBeenCalledTimes(2)
  })
})
