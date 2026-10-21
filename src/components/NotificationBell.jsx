import React, { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertTriangle, Bell, CheckCheck, Info, Megaphone, Sparkles } from "lucide-react"
import { notificationService, updatesService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"
import { w5Support } from "@/i18n/w5Support"
import { cn } from "@/lib/utils"

const POLL_INTERVAL_MS = 20_000
const MAX_BACKOFF_MS = 120_000

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

function isDocumentHidden() { return document.visibilityState === "hidden" }

function formatNotificationDate(raw, lang, recently) {
  if (!raw) return recently
  const date = new Date(raw)
  return Number.isNaN(date.getTime())
    ? recently
    : date.toLocaleString(lang === "ar" ? "ar" : "en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
}

export function NotificationBell({ className }) {
  const navigate = useNavigate()
  const { lang, t } = useLanguage()
  const words = w5Support[lang] || w5Support.en
  const text = (key) => t(key, words[key] || w5Support.en[key] || key)
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const menuRef = useRef(null)
  const notificationsRef = useRef(notifications)
  const requestInFlight = useRef(false)
  const readRequests = useRef(new Set())
  const markAllInFlight = useRef(false)
  const activeRef = useRef(false)
  notificationsRef.current = notifications

  const fetchNotifications = useCallback(async () => {
    if (requestInFlight.current) return false
    requestInFlight.current = true
    if (activeRef.current && notificationsRef.current.length === 0) setLoading(true)
    setError(null)
    try {
      const [personalResult, updatesResult] = await Promise.allSettled([
        notificationService.getNotifications(),
        updatesService.getPublishedUpdates(),
      ])
      if (!activeRef.current) return false
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
        type: update.level || "system",
        category: update.category || "General",
        title: update.title,
        message: update.body || text("updatePublished"),
        link: update.link_url || "/updates",
        is_read: readUpdateReadState(update.id),
        created_at: update.starts_at || update.created_at || null,
      }))
      const merged = [...updateItems, ...personalItems].sort((left, right) => (
        new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime()
      ))
      setNotifications(merged)
      if (personalResult.status !== "fulfilled" || updatesResult.status !== "fulfilled") {
        setError(text("notificationsLoadFailed"))
        return false
      }
      return true
    } catch {
      if (activeRef.current) setError(text("notificationsLoadFailed"))
      return false
    } finally {
      requestInFlight.current = false
      if (activeRef.current) setLoading(false)
    }
  }, [lang, t])

  const fetchRef = useRef(fetchNotifications)
  fetchRef.current = fetchNotifications

  useEffect(() => {
    let stopped = false
    let timer = null
    let failures = 0
    activeRef.current = true

    const schedule = (delay) => {
      if (stopped || isDocumentHidden()) return
      clearTimeout(timer)
      timer = setTimeout(poll, delay)
    }

    const poll = async () => {
      if (stopped || isDocumentHidden()) return
      if (requestInFlight.current) {
        schedule(1000)
        return
      }
      const succeeded = await fetchRef.current()
      if (stopped || isDocumentHidden()) return
      failures = succeeded ? 0 : failures + 1
      const delay = succeeded
        ? POLL_INTERVAL_MS
        : Math.min(POLL_INTERVAL_MS * (2 ** failures), MAX_BACKOFF_MS)
      schedule(delay)
    }

    const onVisibilityChange = () => {
      clearTimeout(timer)
      timer = null
      if (document.visibilityState === "visible") void poll()
    }

    document.addEventListener("visibilitychange", onVisibilityChange)
    void poll()
    return () => {
      stopped = true
      activeRef.current = false
      clearTimeout(timer)
      document.removeEventListener("visibilitychange", onVisibilityChange)
    }
  }, [])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleMarkAsRead = async (notification) => {
    if (!notification || notification.is_read || readRequests.current.has(notification.id)) return
    setActionError(null)
    if (notification.isUpdate) {
      const saved = writeUpdateReadState(notification.originalUpdateId)
      setNotifications((previous) => previous.map((item) => (
        item.id === notification.id ? { ...item, is_read: true } : item
      )))
      if (!saved) setActionError(text("readStateNotSaved"))
      return
    }
    readRequests.current.add(notification.id)
    try {
      await notificationService.markAsRead(notification.id)
      setNotifications((previous) => previous.map((item) => (
        item.id === notification.id ? { ...item, is_read: true } : item
      )))
    } catch {
      setActionError(text("markReadFailed"))
    } finally {
      readRequests.current.delete(notification.id)
    }
  }

  const handleMarkAllRead = async () => {
    if (markAllInFlight.current) return
    markAllInFlight.current = true
    setActionError(null)
    const unreadUpdates = notificationsRef.current.filter((item) => item.isUpdate && !item.is_read)
    const storageFailed = unreadUpdates.some((item) => !writeUpdateReadState(item.originalUpdateId))
    setNotifications((previous) => previous.map((item) => (
      item.isUpdate ? { ...item, is_read: true } : item
    )))
    const unreadPersonal = notificationsRef.current.filter((item) => !item.isUpdate && !item.is_read)
    let personalFailed = false
    if (unreadPersonal.length) {
      try {
        await notificationService.markAllAsRead()
        setNotifications((previous) => previous.map((item) => (
          !item.isUpdate ? { ...item, is_read: true } : item
        )))
      } catch {
        personalFailed = true
      }
    }
    if (personalFailed) setActionError(text("markAllReadFailed"))
    else if (storageFailed) setActionError(text("readStateNotSaved"))
    markAllInFlight.current = false
  }

  const openNotification = (notification) => {
    if (!notification.link) return
    setOpen(false)
    if (!notification.is_read) void handleMarkAsRead(notification)
    if (/^https?:\/\//.test(notification.link)) window.open(notification.link, "_blank", "noopener,noreferrer")
    else navigate(notification.link)
  }

  const getTypeIcon = (type) => {
    if (["alert", "warning", "critical"].includes(type)) return <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" aria-hidden="true" />
    if (type === "creative_found") return <Sparkles className="h-3.5 w-3.5 text-indigo-400 shrink-0" aria-hidden="true" />
    if (type === "system") return <Megaphone className="h-3.5 w-3.5 text-accent shrink-0" aria-hidden="true" />
    return <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" aria-hidden="true" />
  }

  const unreadCount = notifications.filter((item) => !item.is_read).length

  return (
    <div className="relative" ref={menuRef} dir={lang === "ar" ? "rtl" : "ltr"}>
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        className="relative rounded-sm p-1.5 text-text-faint transition-colors hover:bg-surface-2 hover:text-text"
        aria-label={text("notificationsTitle")}
        title={text("notificationsTitle")}
        aria-expanded={open}
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unreadCount > 0 && <span aria-label={text("unreadDot")} className="absolute top-1 end-1 flex h-2 w-2 rounded-full bg-accent animate-pulse" />}
      </button>

      {open && (
        <div className="absolute end-0 bottom-full mb-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-surface-2 p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between gap-2 border-b border-border pb-2 px-2 pt-1">
            <span className="text-xs font-semibold text-text flex items-center gap-1.5">
              <Bell className="h-3.5 w-3.5 text-accent" aria-hidden="true" /> {text("notificationsTitle")}
            </span>
            {unreadCount > 0 && (
              <button type="button" onClick={handleMarkAllRead} className="flex items-center gap-1 text-[11px] text-text-muted hover:text-accent font-mono transition-colors">
                <CheckCheck className="h-3 w-3" aria-hidden="true" /> {text("markAllRead")}
              </button>
            )}
          </div>

          {actionError && <p role="alert" className="mx-2 mt-2 text-[11px] text-amber-300">{actionError}</p>}
          {error && <p role="alert" className="mx-2 mt-2 text-[11px] text-rose-300">{error}</p>}
          <div className="max-h-72 overflow-y-auto divide-y divide-border/40 py-1">
            {loading && notifications.length === 0 ? (
              <div role="status" className="py-6 text-center text-xs text-text-faint">{text("loadingNotifications")}</div>
            ) : notifications.length === 0 ? (
              <div className="py-6 text-center text-xs text-text-faint">{error ? text("notificationsLoadFailed") : text("noNotificationsTitle")}</div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  role={notification.link ? "button" : undefined}
                  tabIndex={notification.link ? 0 : undefined}
                  onClick={() => openNotification(notification)}
                  onKeyDown={(event) => {
                    if (notification.link && (event.key === "Enter" || event.key === " ")) {
                      event.preventDefault()
                      openNotification(notification)
                    }
                  }}
                  className={cn("flex flex-col gap-1 p-2.5 transition-colors rounded-lg text-left my-0.5", notification.link ? "cursor-pointer" : "", !notification.is_read ? "bg-surface-3/70 border border-accent/20" : "hover:bg-surface-3/30")}
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5">
                      {getTypeIcon(notification.type)}
                      <span className="text-xs font-bold text-text">{notification.title}</span>
                    </div>
                    {!notification.is_read && (
                      <button type="button" aria-label={text("markRead")} title={text("markRead")} onClick={(event) => { event.stopPropagation(); void handleMarkAsRead(notification) }} className="text-text-faint hover:text-accent">
                        <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                  <p className="text-[11px] text-text-muted line-clamp-2 leading-relaxed">{notification.message}</p>
                  <div className="flex items-center justify-between gap-2 text-[9px] font-mono text-text-faint uppercase tracking-wider">
                    <span>{notification.category || notification.type}</span>
                    <span>{formatNotificationDate(notification.created_at, lang, text("recently"))}</span>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="flex items-center justify-between border-t border-border/60 pt-2 mt-1 px-2">
            <button type="button" onClick={() => { setOpen(false); navigate("/notifications") }} className="text-[10px] font-mono text-text-muted hover:text-accent transition-colors">{text("viewAllNotifications")}</button>
            <button type="button" onClick={() => { setOpen(false); navigate("/updates") }} className="text-[10px] font-mono text-text-faint hover:text-text transition-colors">{text("platformUpdates")}</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificationBell
