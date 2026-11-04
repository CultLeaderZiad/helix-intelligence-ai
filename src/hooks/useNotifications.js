import { useCallback, useEffect, useRef, useState } from "react"
import { notificationService, updatesService } from "@/services"
import { memberTimestamp } from "@/i18n/memberMessages"
import { invalidateNotificationReads, readNotificationSources } from "@/hooks/notificationReadCache"

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

export function useNotifications(fallbackUpdateBody, { scope = null } = {}) {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [dataScope, setDataScope] = useState(scope)
  const dataScopeRef = useRef(scope)
  const scopeRef = useRef(scope)
  scopeRef.current = scope
  const requestInFlight = useRef(null)
  const markAllInFlight = useRef(false)
  const scopedNotifications = dataScope === scope ? notifications : []
  const scopedLoading = dataScope === scope ? loading : true
  const scopedError = dataScope === scope ? error : false
  const scopedActionError = dataScope === scope ? actionError : null
  const notificationsRef = useRef(scopedNotifications)
  notificationsRef.current = scopedNotifications

  const load = useCallback(async (force = false) => {
    const requestScope = scope
    if (requestInFlight.current?.scope === requestScope) return false
    const request = { scope: requestScope }
    requestInFlight.current = request
    if (dataScopeRef.current !== requestScope) {
      dataScopeRef.current = requestScope
      setDataScope(requestScope)
      setNotifications([])
      setActionError(null)
    }
    setLoading(true)
    setError(false)
    try {
      const [personalResult, updatesResult] = await readNotificationSources(requestScope, { force })
      if (scopeRef.current !== requestScope || requestInFlight.current !== request) return false
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
      if (scopeRef.current === requestScope) setError(true)
      return false
    } finally {
      if (requestInFlight.current === request) requestInFlight.current = null
      if (scopeRef.current === requestScope) setLoading(false)
    }
  }, [fallbackUpdateBody, scope])

  const refresh = useCallback(() => load(true), [load])
  useEffect(() => {
    void load(false)
  }, [load])

  const markAsRead = useCallback(async (notification) => {
    setActionError(null)
    if (notification.isUpdate) {
      const saved = writeUpdateReadState(notification.originalUpdateId)
      if (saved) invalidateNotificationReads(scope)
      if (scopeRef.current === scope) {
        setNotifications((previous) => previous.map((item) => (
          item.id === notification.id ? { ...item, is_read: true } : item
        )))
        if (!saved) setActionError("readStateNotSaved")
      }
      return saved
    }
    try {
      await notificationService.markAsRead(notification.id)
      if (scopeRef.current === scope) {
        invalidateNotificationReads(scope)
        setNotifications((previous) => previous.map((item) => (
          item.id === notification.id ? { ...item, is_read: true } : item
        )))
      }
      return true
    } catch {
      if (scopeRef.current === scope) setActionError("markReadFailed")
      return false
    }
  }, [scope])

  const markAllRead = useCallback(async () => {
    if (markAllInFlight.current) return false
    markAllInFlight.current = true
    setActionError(null)
    const snapshot = notificationsRef.current
    const unreadUpdates = snapshot.filter((item) => item.isUpdate && !item.is_read)
    const storageFailed = unreadUpdates.some((item) => !writeUpdateReadState(item.originalUpdateId))
    if (unreadUpdates.length) invalidateNotificationReads(scope)
    if (scopeRef.current === scope) {
      setNotifications((previous) => previous.map((item) => (
        item.isUpdate ? { ...item, is_read: true } : item
      )))
    }
    const unreadPersonal = snapshot.filter((item) => !item.isUpdate && !item.is_read)
    try {
      if (unreadPersonal.length) {
        try {
          await notificationService.markAllAsRead()
          invalidateNotificationReads(scope)
          if (scopeRef.current === scope) {
            setNotifications((previous) => previous.map((item) => (
              !item.isUpdate ? { ...item, is_read: true } : item
            )))
          }
        } catch {
          if (scopeRef.current === scope) setActionError("markAllReadFailed")
          return false
        }
      }
      if (storageFailed && scopeRef.current === scope) setActionError("readStateNotSaved")
      return !storageFailed
    } finally {
      markAllInFlight.current = false
    }
  }, [scope])

  return {
    notifications: scopedNotifications,
    loading: scopedLoading,
    error: scopedError,
    actionError: scopedActionError,
    refresh,
    markAsRead,
    markAllRead,
  }
}
