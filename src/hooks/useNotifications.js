import { useCallback, useEffect, useRef, useState } from "react"
import { notificationService, updatesService } from "@/services"
import { memberTimestamp } from "@/i18n/memberMessages"

function readUpdateReadState(id) {
  try {
    return window.localStorage.getItem(`helix_update_read_${id}`) === "true"
  } catch {
    return false
  }
}

function writeUpdateReadState(id) {
  try {
    window.localStorage.setItem(`helix_update_read_${id}`, "true")
    return true
  } catch {
    return false
  }
}

export function useNotifications(fallbackUpdateBody) {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [actionError, setActionError] = useState(null)
  const requestInFlight = useRef(false)
  const markAllInFlight = useRef(false)
  const notificationsRef = useRef(notifications)
  notificationsRef.current = notifications

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return false
    requestInFlight.current = true
    setLoading(true)
    setError(false)
    try {
      const [personalResult, updatesResult] = await Promise.allSettled([
        notificationService.getNotifications(),
        updatesService.getPublishedUpdates(),
      ])
      const previous = notificationsRef.current
      const personalItems = personalResult.status === "fulfilled"
        ? (Array.isArray(personalResult.value?.items) ? personalResult.value.items : [])
        : previous.filter((item) => !item.isUpdate)
      const publishedUpdates = updatesResult.status === "fulfilled"
        ? (Array.isArray(updatesResult.value) ? updatesResult.value : [])
        : previous.filter((item) => item.isUpdate)
      const updateItems = publishedUpdates.map((update) => ({
        id: `update_${update.id}`,
        originalUpdateId: update.id,
        isUpdate: true,
        type: "announcement",
        level: update.level || "info",
        category: update.category || "General",
        title: update.title,
        message: update.body || fallbackUpdateBody,
        link: update.link_url || "/updates",
        is_read: readUpdateReadState(update.id),
        created_at: update.starts_at || update.created_at || null,
      }))
      const merged = [...updateItems, ...personalItems].sort((left, right) => (
        memberTimestamp(right.created_at) - memberTimestamp(left.created_at)
      ))
      setNotifications(merged)
      const succeeded = personalResult.status === "fulfilled" && updatesResult.status === "fulfilled"
      if (!succeeded) setError(true)
      return succeeded
    } catch {
      setError(true)
      return false
    } finally {
      requestInFlight.current = false
      setLoading(false)
    }
  }, [fallbackUpdateBody])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const markAsRead = useCallback(async (notification) => {
    setActionError(null)
    if (notification.isUpdate) {
      const saved = writeUpdateReadState(notification.originalUpdateId)
      setNotifications((previous) => previous.map((item) => (
        item.id === notification.id ? { ...item, is_read: true } : item
      )))
      if (!saved) setActionError("readStateNotSaved")
      return saved
    }
    try {
      await notificationService.markAsRead(notification.id)
      setNotifications((previous) => previous.map((item) => (
        item.id === notification.id ? { ...item, is_read: true } : item
      )))
      return true
    } catch {
      setActionError("markReadFailed")
      return false
    }
  }, [])

  const markAllRead = useCallback(async () => {
    if (markAllInFlight.current) return false
    markAllInFlight.current = true
    setActionError(null)
    const snapshot = notificationsRef.current
    const unreadUpdates = snapshot.filter((item) => item.isUpdate && !item.is_read)
    const storageFailed = unreadUpdates.some((item) => !writeUpdateReadState(item.originalUpdateId))
    setNotifications((previous) => previous.map((item) => (
      item.isUpdate ? { ...item, is_read: true } : item
    )))
    const unreadPersonal = snapshot.filter((item) => !item.isUpdate && !item.is_read)
    let personalFailed = false
    try {
      if (unreadPersonal.length) {
        await notificationService.markAllAsRead()
        setNotifications((previous) => previous.map((item) => (
          !item.isUpdate ? { ...item, is_read: true } : item
        )))
      }
      if (personalFailed) setActionError("markAllReadFailed")
      else if (storageFailed) setActionError("readStateNotSaved")
      return !personalFailed && !storageFailed
    } catch {
      personalFailed = true
      setActionError("markAllReadFailed")
      return false
    } finally {
      markAllInFlight.current = false
    }
  }, [])

  return { notifications, loading, error, actionError, refresh, markAsRead, markAllRead }
}
