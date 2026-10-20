import { Activity } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { useTelemetry } from "@/app/TelemetryContext"
import { useAuth } from "@/context/AuthContext"
import { useLanguage } from "@/context/LanguageContext"

export function StatusBar() {
  const { telemetry } = useTelemetry()
  const { user } = useAuth()
  const { t } = useLanguage()
  const location = useLocation()
  const showAdminDiagnostics = location.pathname.startsWith("/admin") && user?.role === "admin"

  return (
    <footer className="flex h-6 shrink-0 items-center justify-between border-t border-border bg-bg px-3 font-mono text-[10px] text-text-faint">
      <div className="flex min-w-0 items-center gap-2 truncate">
        <Activity className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
        <span>{t("workspaceStatus")}</span>
        {showAdminDiagnostics && (
          <span>{t("requestsLabel")}: {telemetry.requests}</span>
        )}
        {showAdminDiagnostics && telemetry.latency != null && (
          <span>{telemetry.latency} ms</span>
        )}
      </div>
      <Link to="/support" className="hover:text-text-muted">{t("supportLabel")}</Link>
    </footer>
  )
}
