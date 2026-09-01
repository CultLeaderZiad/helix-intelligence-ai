import React, { useState, useEffect } from "react"
import { Bell, Check, CheckCheck, Info, AlertTriangle, Sparkles, Megaphone, Trash2, RefreshCw } from "lucide-react"
import { notificationService } from "@/services"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

export function NotificationsPage() {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState("all")

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const res = await notificationService.getNotifications()
      setNotifications(res.items || [])
    } catch (err) {
      console.error("Failed to load notifications", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNotifications()
  }, [])

  const handleMarkAsRead = async (id) => {
    try {
      await notificationService.markAsRead(id)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      )
    } catch (err) {
      console.error(err)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllAsRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    } catch (err) {
      console.error(err)
    }
  }

  const filtered = notifications.filter((n) => {
    if (filterType === "unread") return !n.is_read
    if (filterType === "alert") return n.type === "alert" || n.type === "quota"
    if (filterType === "announcement") return n.type === "broadcast" || n.type === "announcement"
    return true
  })

  const unreadCount = notifications.filter((n) => !n.is_read).length

  const getTypeBadge = (type) => {
    switch (type) {
      case "alert":
      case "quota":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <AlertTriangle className="h-3 w-3" /> Alert
          </span>
        )
      case "broadcast":
      case "announcement":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-teal-500/10 text-teal-300 border border-teal-500/20">
            <Megaphone className="h-3 w-3" /> Announcement
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            <Info className="h-3 w-3" /> System
          </span>
        )
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-slate-950 text-slate-100">
      <BreadcrumbBar
        trail={["Helix", "Workspace", "Notifications & Messages"]}
        meta={`${notifications.length} messages (${unreadCount} unread)`}
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="outline"
              onClick={fetchNotifications}
              className="flex items-center gap-1"
            >
              <RefreshCw className="h-3 w-3" /> Refresh
            </Button>
            {unreadCount > 0 && (
              <Button
                size="xs"
                variant="primary"
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 font-mono text-[11px]"
              >
                <CheckCheck className="h-3.5 w-3.5" /> Mark all as read
              </Button>
            )}
          </div>
        }
      />

      <div className="p-6 max-w-5xl mx-auto w-full space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-teal-400" />
              Notifications & Announcements
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Live broadcast messages, credit alerts, feature updates, and support responses.
            </p>
          </div>

          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
            {[
              { id: "all", label: "All" },
              { id: "unread", label: `Unread (${unreadCount})` },
              { id: "announcement", label: "Announcements" },
              { id: "alert", label: "Alerts" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterType(tab.id)}
                className={cn(
                  "px-3 py-1 text-xs rounded-md font-medium transition",
                  filterType === tab.id
                    ? "bg-teal-500/10 text-teal-300 border border-teal-500/30"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Notifications List */}
        {loading ? (
          <div className="py-20 text-center text-slate-500 font-mono text-xs">
            Loading messages and announcements...
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center text-slate-500 space-y-2">
            <Bell className="w-8 h-8 mx-auto text-slate-600 opacity-50" />
            <p className="text-sm font-medium text-slate-400">No notifications in this view</p>
            <p className="text-xs text-slate-500">You're all caught up with platform broadcasts and alerts.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((n) => (
              <div
                key={n.id}
                className={cn(
                  "p-4 rounded-xl border transition flex flex-col sm:flex-row sm:items-start justify-between gap-4",
                  !n.is_read
                    ? "bg-slate-900/90 border-teal-500/30 shadow-lg shadow-teal-500/5"
                    : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700"
                )}
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2.5">
                    {getTypeBadge(n.type)}
                    <h3 className="text-sm font-bold text-slate-100">{n.title}</h3>
                    {!n.is_read && (
                      <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                    )}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line font-sans">
                    {n.message}
                  </p>
                  <div className="text-[11px] font-mono text-slate-500">
                    {n.created_at ? new Date(n.created_at).toLocaleString() : "Just now"}
                  </div>
                </div>

                {!n.is_read && (
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => handleMarkAsRead(n.id)}
                    className="self-start text-slate-400 hover:text-teal-300 hover:border-teal-500/30 font-mono text-[11px]"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" /> Mark read
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default NotificationsPage
