import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { accountService, notificationService, supportService, updatesService } from "@/services"
import { formatMemberDate, getMemberMessage, getMemberRoleLabel, memberMessages, memberTimestamp } from "@/i18n/memberMessages"
import { useNotifications } from "@/hooks/useNotifications"
import { useProfileSettings } from "@/hooks/useProfileSettings"
import { useSupport } from "@/hooks/useSupport"

vi.mock("@/services", () => ({
  accountService: {
    getProfile: vi.fn(),
    uploadAvatar: vi.fn(),
    updateProfile: vi.fn(),
  },
  authService: { restartOnboarding: vi.fn() },
  notificationService: {
    getNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
  },
  supportService: {
    listTickets: vi.fn(),
    getTicket: vi.fn(),
    replyTicket: vi.fn(),
  },
  updatesService: { getPublishedUpdates: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
  vi.mocked(accountService.getProfile).mockResolvedValue({ full_name: "Ada", email: "ada@example.test", role: "member" })
  vi.mocked(accountService.uploadAvatar).mockResolvedValue({ avatar_url: "https://example.test/avatar.png" })
  vi.mocked(accountService.updateProfile).mockResolvedValue({ full_name: "Ada Lovelace", avatar_url: "https://example.test/avatar.png" })
  vi.mocked(supportService.listTickets).mockResolvedValue([])
  vi.mocked(supportService.getTicket).mockResolvedValue({ id: "ticket-1", replies: [] })
  vi.mocked(supportService.replyTicket).mockResolvedValue({ id: "reply-1", message: "Thanks" })
  vi.mocked(notificationService.getNotifications).mockResolvedValue({ items: [] })
  vi.mocked(notificationService.markAsRead).mockResolvedValue({ ok: true })
  vi.mocked(notificationService.markAllAsRead).mockResolvedValue({ ok: true })
  vi.mocked(updatesService.getPublishedUpdates).mockResolvedValue([])
})

describe("member message and date helpers", () => {
  it("provides complete English and Arabic profile copy", () => {
    expect(Object.keys(memberMessages.ar).sort()).toEqual(Object.keys(memberMessages.en).sort())
    for (const key of Object.keys(memberMessages.en)) {
      expect(getMemberMessage("ar", key)).toBe(memberMessages.ar[key])
      expect(memberMessages.ar[key]).not.toBe(memberMessages.en[key])
    }
    expect(getMemberRoleLabel("ar", "organization_admin")).toBe(memberMessages.ar.profileRoleAdmin)
  })

  it("formats valid dates by locale and gives a safe fallback for missing or invalid values", () => {
    expect(formatMemberDate(null, "ar", "حديثًا")).toBe("حديثًا")
    expect(formatMemberDate("not-a-date", "ar", "حديثًا")).toBe("حديثًا")
    expect(formatMemberDate("2026-10-21T12:00:00Z", "ar", "حديثًا")).not.toBe("حديثًا")
    expect(memberTimestamp("not-a-date")).toBe(0)
    expect(memberTimestamp(null)).toBe(0)
  })
})

describe("useProfileSettings", () => {
  it("loads, uploads, and saves profile data using the account PATCH payload", async () => {
    const { result } = renderHook(() => useProfileSettings())
    await waitFor(() => expect(result.current.profile.full_name).toBe("Ada"))
    expect(result.current.isLoadingProfile).toBe(false)

    const avatar = new File(["image"], "avatar.png", { type: "image/png" })
    await act(async () => { await result.current.uploadAvatar(avatar) })
    expect(accountService.uploadAvatar).toHaveBeenCalledWith(avatar)
    expect(result.current.profile.avatar_url).toBe("https://example.test/avatar.png")

    await act(async () => {
      await result.current.saveProfile({
        fullName: "Ada Lovelace",
        avatarUrl: "https://example.test/avatar.png",
        currentPassword: "current-password",
        newPassword: "new-password-123",
      })
    })
    expect(accountService.updateProfile).toHaveBeenCalledWith({
      full_name: "Ada Lovelace",
      avatar_url: "https://example.test/avatar.png",
      current_password: "current-password",
      new_password: "new-password-123",
    })
    expect(result.current.profile.full_name).toBe("Ada Lovelace")
    expect(result.current.isSaving).toBe(false)
  })

  it("exposes profile-load failures and clears loading state", async () => {
    vi.mocked(accountService.getProfile).mockRejectedValueOnce(new Error("offline"))
    const { result } = renderHook(() => useProfileSettings())
    await waitFor(() => expect(result.current.loadError).toBe(true))
    expect(result.current.isLoadingProfile).toBe(false)
  })
})

describe("useSupport", () => {
  it("loads the selected ticket, trims replies, and exposes reply failures", async () => {
    vi.mocked(supportService.listTickets).mockResolvedValueOnce([{ id: "ticket-1" }])
    vi.mocked(supportService.getTicket).mockResolvedValueOnce({ id: "ticket-1", replies: [] })
    vi.mocked(supportService.replyTicket).mockRejectedValueOnce(new Error("offline"))
    const { result } = renderHook(() => useSupport())

    await waitFor(() => expect(result.current.ticketDetails?.id).toBe("ticket-1"))
    await act(async () => { await result.current.sendReply("ticket-1", "  help please  ") })
    expect(supportService.replyTicket).toHaveBeenCalledWith("ticket-1", "help please")
    expect(result.current.errorCode).toBe("replyFailed")
    expect(result.current.isSendingReply).toBe(false)

    await act(async () => { await result.current.sendReply("ticket-1", "resolved") })
    expect(result.current.ticketDetails.replies).toHaveLength(1)
    expect(result.current.errorCode).toBe(null)
  })
})

describe("useNotifications", () => {
  it("merges notifications safely and reports failed mark-all actions", async () => {
    vi.mocked(notificationService.getNotifications).mockResolvedValueOnce({
      items: [{ id: "notice-1", type: "system", is_read: false, created_at: "2026-10-21T10:00:00Z" }],
    })
    vi.mocked(updatesService.getPublishedUpdates).mockResolvedValueOnce([
      { id: "update-1", title: "Release", created_at: "invalid-date" },
    ])
    vi.mocked(notificationService.markAllAsRead).mockRejectedValueOnce(new Error("offline"))
    const { result } = renderHook(() => useNotifications("Update published"))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe(false)
    expect(result.current.notifications).toHaveLength(2)
    expect(result.current.notifications[0].id).toBe("notice-1")

    await act(async () => { await result.current.markAllRead() })
    expect(result.current.actionError).toBe("markAllReadFailed")
    expect(result.current.notifications.find((item) => item.id === "notice-1").is_read).toBe(false)
    expect(result.current.notifications.find((item) => item.isUpdate).is_read).toBe(true)
  })
})
