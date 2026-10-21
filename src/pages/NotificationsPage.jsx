import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertTriangle, Bell, Check, CheckCheck, Info, Megaphone, RefreshCw } from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { useLanguage } from "@/context/LanguageContext"
import { w5Support } from "@/i18n/w5Support"
import { formatMemberDate } from "@/i18n/memberMessages"
import { useNotifications } from "@/hooks/useNotifications"
import { cn } from "@/lib/utils"

export function NotificationsPage() {
  const navigate = useNavigate()
  const { lang, t } = useLanguage()
  const words = w5Support[lang] || w5Support.en
  const text = (key) => t(key, words[key] || w5Support.en[key] || key)
  const { notifications, loading, error, actionError, refresh, markAsRead, markAllRead } = useNotifications(text("updatePublished"))
  const [filterType, setFilterType] = useState("all")

  const filtered = notifications.filter((item) => {
    if (filterType === "unread") return !item.is_read
    if (filterType === "alert") return ["alert", "quota", "warning", "critical"].includes(item.type)
    if (filterType === "announcement") return ["broadcast", "announcement"].includes(item.type)
    return true
  })
  const unreadCount = notifications.filter((item) => !item.is_read).length

  const getTypeBadge = (type) => {
    if (["alert", "quota", "warning", "critical"].includes(type)) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20"><AlertTriangle className="h-3 w-3" aria-hidden="true" />{text("alert")}</span>
    }
    if (["broadcast", "announcement"].includes(type)) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-teal-500/10 text-teal-300 border border-teal-500/20"><Megaphone className="h-3 w-3" aria-hidden="true" />{text("announcement")}</span>
    }
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"><Info className="h-3 w-3" aria-hidden="true" />{text("system")}</span>
  }

  const openLink = (link) => {
    if (!link) return
    if (link.startsWith("http")) window.open(link, "_blank", "noopener,noreferrer")
    else navigate(link)
  }

  return (
    <div className="w-full flex-1 flex flex-col bg-slate-950 text-slate-100 font-sans" dir={lang === "ar" ? "rtl" : "ltr"}>
      <BreadcrumbBar
        trail={["Helix", text("workspace"), text("notificationsTitle")]}
        meta={text("messageCount").replace("{count}", String(notifications.length)).replace("{unread}", String(unreadCount))}
        actions={(
          <div className="flex items-center gap-2">
            <a href="/updates" className="inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-1 rounded border border-slate-700 bg-slate-900 text-teal-300 hover:border-teal-500/40 transition-colors">
              <span>{text("platformUpdates")}</span><span aria-hidden="true" className="text-xs">↗</span>
            </a>
            <Button size="xs" variant="outline" onClick={() => void refresh()} disabled={loading} className="flex items-center gap-1">
              <RefreshCw className="h-3 w-3" aria-hidden="true" /> {text("refresh")}
            </Button>
            {unreadCount > 0 && (
              <Button size="xs" variant="primary" onClick={() => void markAllRead()} className="flex items-center gap-1 font-mono text-[11px]">
                <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" /> {text("markAllRead")}
              </Button>
            )}
          </div>
        )}
      />

      <div className="p-6 max-w-5xl mx-auto w-full space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2"><Bell className="w-5 h-5 text-teal-400" aria-hidden="true" />{text("notificationsTitle")}</h1>
            <p className="text-xs text-slate-400 mt-1">{text("notificationsSubtitle")}</p>
          </div>
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
            {[
              { id: "all", label: text("all") },
              { id: "unread", label: text("unread").replace("{count}", String(unreadCount)) },
              { id: "announcement", label: text("announcements") },
              { id: "alert", label: text("alerts") },
            ].map((tab) => (
              <button key={tab.id} type="button" aria-pressed={filterType === tab.id} onClick={() => setFilterType(tab.id)} className={cn("px-3 py-1 text-xs rounded-md font-medium transition", filterType === tab.id ? "bg-teal-500/10 text-teal-300 border border-teal-500/30" : "text-slate-400 hover:text-slate-200")}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {actionError && <div role="alert" className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">{text(actionError)}</div>}
        {error && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">{text("notificationsLoadFailed")}</div>}

        {loading && notifications.length === 0 ? (
          <div role="status" className="py-20 text-center text-slate-500 font-mono text-xs">{text("loadingNotifications")}</div>
        ) : error && notifications.length === 0 ? (
          <div role="alert" className="rounded-2xl border border-dashed border-rose-500/30 p-12 text-center text-rose-200 space-y-3">
            <p className="text-sm">{text("notificationsLoadFailed")}</p>
            <Button size="xs" variant="outline" onClick={() => void refresh()}>{text("refresh")}</Button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center text-slate-500 space-y-2">
            <Bell className="w-8 h-8 mx-auto text-slate-600 opacity-50" aria-hidden="true" />
            <p className="text-sm font-medium text-slate-400">{notifications.length === 0 ? text("noNotificationsTitle") : text("noFilterMatches")}</p>
            {notifications.length === 0 && !error && <p className="text-xs text-slate-500">{text("noNotificationsDescription")}</p>}
            {error && <Button size="xs" variant="outline" onClick={() => void refresh()}>{text("refresh")}</Button>}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((notification) => (
              <div key={notification.id} className={cn("p-4 rounded-xl border transition flex flex-col sm:flex-row sm:items-start justify-between gap-4", !notification.is_read ? "bg-slate-900/90 border-teal-500/30 shadow-lg shadow-teal-500/5" : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700")}>
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {getTypeBadge(notification.type)}
                    {notification.isUpdate && notification.category && <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">{notification.category}</span>}
                    <h2 className="text-sm font-bold text-slate-100">{notification.title}</h2>
                    {!notification.is_read && <span aria-label={text("unread").replace("{count}", "")} className="w-2 h-2 rounded-full bg-teal-400" />}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line font-sans">{notification.message}</p>
                  <p className="text-[11px] font-mono text-slate-500">{formatMemberDate(notification.created_at, lang, text("recently"))}</p>
                  {notification.link && (
                    <button type="button" onClick={() => { if (!notification.is_read) void markAsRead(notification); openLink(notification.link) }} className="text-[11px] font-mono text-teal-300 hover:underline text-left inline-flex items-center gap-1 mt-1">
                      {notification.isUpdate ? text("platformUpdates") : text("openNotification")}
                    </button>
                  )}
                </div>
                {!notification.is_read && (
                  <Button size="xs" variant="outline" onClick={() => void markAsRead(notification)} className="self-start text-slate-400 hover:text-teal-300 hover:border-teal-500/30 font-mono text-[11px]">
                    <Check className="w-3.5 h-3.5 mr-1" aria-hidden="true" /> {text("markRead")}
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
