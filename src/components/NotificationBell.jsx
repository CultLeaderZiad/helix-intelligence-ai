import React, { useState, useEffect, useRef } from "react"
import { Bell, Check, ExternalLink, Info, AlertTriangle, Sparkles, CheckCheck } from "lucide-react"
import { notificationService } from "@/services"
import { cn } from "@/lib/utils"

export function NotificationBell({ className }) {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const menuRef = useRef(null)

  const fetchNotifications = async () => {
    try {
      const res = await notificationService.getNotifications()
      setNotifications(res.items || [])
      setUnreadCount(res.unread_count || 0)
    } catch (err) {
      console.error("Failed to load notifications", err)
    }
  }

  useEffect(() => {
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 30000) // Poll every 30s
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
    e.stopPropagation()
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
      await notificationService.markAllAsRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error(err)
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case "alert":
      case "quota":
        return <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
      case "creative_found":
        return <Sparkles className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
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
        <div className="absolute right-0 bottom-full mb-2 w-80 rounded-lg border border-border bg-surface-2 p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b border-border pb-2 px-2 pt-1">
            <span className="text-xs font-semibold text-text">Notifications</span>
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
                  className={cn(
                    "flex flex-col gap-1 p-2 transition-colors rounded-sm text-left",
                    !n.is_read ? "bg-surface-3/50" : "hover:bg-surface-3/30"
                  )}
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5">
                      {getTypeIcon(n.type)}
                      <span className="text-xs font-semibold text-text">{n.title}</span>
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(n.id, e)}
                        className="text-text-faint hover:text-accent p-0.5"
                        title="Mark as read"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed pl-5">
                    {n.message}
                  </p>
                  <span className="text-[10px] font-mono text-text-faint pl-5">
                    {n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
