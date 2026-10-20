import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { LogOut, Shield, HelpCircle, Settings, Bell, BookOpen, KeyRound, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"
import { authService } from "@/services"
import { NAV_SECTIONS } from "./navigation"
import { NotificationBell } from "@/components/NotificationBell"
import { ONBOARDING_TOUR_RESTART_EVENT } from "@/i18n/w5Onboarding"

export function Sidebar({ className = "", onOpenCommand = null }) {
  const { user, signOut, updateUser } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [tourError, setTourError] = useState(false)
  void onOpenCommand
  const links = [
    ...NAV_SECTIONS.map((section) => ({ ...section, text: t(section.key, section.label) })),
    { path: "/access", text: t("accessUsage"), icon: KeyRound },
    { path: "/docs", text: t("docsNavigation"), icon: BookOpen },
    { path: "/support", text: t("supportNavigation"), icon: MessageSquare },
    { path: "/settings", text: t("settingsNavigation"), icon: Settings },
    { path: "/notifications", text: t("updatesNavigation"), icon: Bell },
    ...(user?.role === "admin" ? [{ path: "/admin", text: t("adminConsoleLabel"), icon: Shield }] : []),
  ]

  async function restartTour() {
    setTourError(false)
    setBusy(true)
    try {
      await authService.restartOnboarding()
      updateUser({ has_completed_onboarding: false })
      if (window.location.pathname === "/discover") {
        window.dispatchEvent(new CustomEvent(ONBOARDING_TOUR_RESTART_EVENT, { detail: { persisted: true } }))
      } else navigate("/discover?tour=restart")
    } catch { setTourError(true) }
    finally { setBusy(false) }
  }

  return (
    <nav className={cn("flex w-[210px] shrink-0 flex-col border-e border-border bg-surface select-none", className)} aria-label={t("primaryNavigation")}>
      <NavLink to="/discover" className="flex h-12 items-center gap-2 border-b border-border px-3 font-semibold">
        <img src="/brand/helix-mark.svg" alt="" className="h-5 w-5" />Helix Intelligence
      </NavLink>
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        <p className="label-mono px-2 py-2 text-text-faint">{t("workspaceNavigation")}</p>
        {links.map(({ path, text, icon: Icon }) => (
          <NavLink key={path} to={path} id={path === "/discover" ? "tour-discover-nav" : undefined}
            className={({ isActive }) => cn("flex items-center gap-2 rounded-sm px-2 py-2 text-sm", isActive ? "bg-surface-3 font-semibold text-text" : "text-text-muted hover:bg-surface-2 hover:text-text")}>
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" /><span>{text}</span>
          </NavLink>
        ))}
      </div>
      <div className="space-y-2 border-t border-border p-3">
        <p className="truncate text-xs text-text-muted">{user?.name || user?.email}</p>
        {tourError && <p role="alert" className="text-xs text-danger">{t("tourRestartFailed")}</p>}
        <div className="flex items-center gap-3">
          <NotificationBell />
          <button type="button" onClick={restartTour} disabled={busy} aria-label={t("helpTour")} title={t("helpTour")} className="text-text-muted hover:text-text disabled:opacity-50"><HelpCircle className="h-4 w-4" /></button>
          <button type="button" onClick={signOut} aria-label={t("logout")} title={t("logout")} className="text-text-muted hover:text-text"><LogOut className="h-4 w-4" /></button>
        </div>
      </div>
    </nav>
  )
}
