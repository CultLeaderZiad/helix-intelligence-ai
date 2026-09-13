import React, { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Bell, Check, ExternalLink, Info, AlertTriangle, Sparkles, CheckCheck, Megaphone } from "lucide-react"
import { notificationService, updatesService } from "@/services"
import { cn } from "@/lib/utils"

function formatNotificationDate(raw) {
  if (!raw) return "Recently"
  try {
    let s = String(raw).trim()
    if (!s) return "Recently"
    if (s.includes(" ") && !s.includes("T")) {
      s = s.replace(" ", "T")
    }
    if (!s.endsWith("Z") && !s.includes("+") && !s.includes("-", 10)) {
      s += "Z"
    }
    const d = new Date(s)
    if (isNaN(d.getTime())) {
      const d2 = new Date(raw)
      if (!isNaN(d2.getTime())) {
        return d2.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
      }
      return "Recently"
    }
    return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
  } catch {
    return "Recently"
  }
}

export function NotificationBell({ className }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const menuRef = useRef(null)

  const fetchNotifications = async () => {
    try {
      const [res, publishedUpdates] = await Promise.all([
        notificationService.getNotifications().catch(() => ({ items: [], unread_count: 0 })),
        updatesService.getPublishedUpdates().catch(() => [])
      ])

      const updateItems = (Array.isArray(publishedUpdates) ? publishedUpdates : []).map((u) => {
        const isRead = localStorage.getItem(`helix_update_read_${u.id}`) === "true"
        return {
          id: `update_${u.id}`,
          originalUpdateId: u.id,
          isUpdate: true,
          type: u.level || "system",
          title: u.title,
          message: u.body || "System update published.",
          link: u.link_url || null,
          is_read: isRead,
          created_at: u.created_at || new Date().toISOString(),
        }
      })

      const personalItems = res?.items || []
      const merged = [...updateItems, ...personalItems].sort((a, b) => {
        const da = new Date(a.created_at || 0).getTime()
        const db = new Date(b.created_at || 0).getTime()
        return db - da
      })

      const totalUnread = merged.filter((item) => !item.is_read).length
      setNotifications(merged)
      setUnreadCount(totalUnread)
    } catch (err) {
      console.error("Failed to load notifications", err)
    }
  }

  useEffect(() => {
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 20000) // Poll every 20s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleMarkAsRead = async (id, e) => {
    if (e) e.stopPropagation()
    const target = notifications.find((n) => n.id === id)
    if (target?.isUpdate) {
      localStorage.setItem(`helix_update_read_${target.originalUpdateId}`, "true")
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      )
      setUnreadCount((c) => Math.max(0, c - 1))
      return
    }
    try {
      await notificationService.markAsRead(id)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      )
      setUnreadCount((c) => Math.max(0, c - 1))
    } catch (err) {
      console.error(err)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      notifications.forEach((n) => {
        if (n.isUpdate) {
          localStorage.setItem(`helix_update_read_${n.originalUpdateId}`, "true")
        }
      })
      await notificationService.markAllAsRead().catch(() => {})
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error(err)
    }
  }

  const openNotification = (n) => {
    if (!n.link) return
    setOpen(false)
    if (!n.is_read) {
      handleMarkAsRead(n.id)
    }
    if (n.link.startsWith("http")) {
      window.open(n.link, "_blank", "noopener,noreferrer")
    } else {
      navigate(n.link)
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case "alert":
      case "warning":
      case "critical":
        return <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
      case "creative_found":
        return <Sparkles className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
      case "system":
        return <Megaphone className="h-3.5 w-3.5 text-accent shrink-0" />
      default:
        return <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
    }
  }

  return (
    <div className={cn("relative", className)} ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="relative rounded-sm p-1.5 text-text-faint transition-colors hover:bg-surface-2 hover:text-text"
        aria-label="Notifications"
        title="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-2 w-2 items-center justify-center rounded-full bg-accent animate-pulse" />
        )}
      </button>

      {open && (
        <div className="absolute left-0 bottom-full mb-2 w-80 rounded-xl border border-border bg-surface-2 p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b border-border pb-2 px-2 pt-1">
            <span className="text-xs font-semibold text-text flex items-center gap-1.5">
              <Bell className="h-3.5 w-3.5 text-accent" />
              Notifications & Updates
            </span>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-[11px] text-text-muted hover:text-accent font-mono transition-colors"
              >
                <CheckCheck className="h-3 w-3" />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-72 overflow-y-auto divide-y divide-border/40 py-1">
            {notifications.length === 0 ? (
              <div className="py-6 text-center text-xs text-text-faint">
                No notifications right now
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  role={n.link ? "button" : undefined}
                  tabIndex={n.link ? 0 : undefined}
                  onClick={() => openNotification(n)}
                  onKeyDown={(e) => {
                    if (n.link && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault()
                      openNotification(n)
                    }
                  }}
                  className={cn(
                    "flex flex-col gap-1 p-2.5 transition-colors rounded-lg text-left my-0.5",
                    n.link ? "cursor-pointer" : "",
                    !n.is_read ? "bg-surface-3/70 border border-accent/20" : "hover:bg-surface-3/30"
                  )}
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5">
                      {getTypeIcon(n.type)}
                      <span className="text-xs font-bold text-text">{n.title}</span>
                      {n.link ? <ExternalLink className="h-3 w-3 text-text-faint shrink-0" /> : null}
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(n.id, e)}
                        className="text-text-faint hover:text-accent p-0.5 rounded transition"
                        title="Mark as read"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed pl-5 whitespace-pre-line font-sans">
                    {n.message}
                  </p>
                  <span className="text-[10px] font-mono text-text-faint pl-5">
                    {formatNotificationDate(n.created_at)}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="border-t border-border pt-2 px-2 text-center">
            <a
              href="/notifications"
              onClick={() => setOpen(false)}
              className="text-[11px] font-mono text-accent hover:underline inline-flex items-center gap-1"
            >
              <span>View All Messages & Updates →</span>
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificationBell
