import { useEffect } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { DiscoverPage } from "@/pages/DiscoverPage"
import { PendingLoopPage } from "@/pages/PendingLoopPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

/**
 * Root component. Deliberately thin: it mounts shell-level providers,
 * the chrome, and the route table — nothing else. `BrowserRouter` lives
 * in main.jsx so this component stays testable without a router mock.
 *
 * Routes are derived from NAV_SECTIONS so a loop can never exist in the
 * sidebar without a matching route.
 */
function DocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const section = NAV_SECTIONS.find((s) => pathname.startsWith(s.path))
    document.title = section
      ? `${section.label} · Helix Intelligence`
      : "Helix Intelligence"
  }, [pathname])

  return null
}

export default function App() {
  return (
    <TelemetryProvider>
      <DocumentTitle />
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/discover" replace />} />
          <Route path="/discover" element={<DiscoverPage />} />
          {NAV_SECTIONS.filter((s) => s.status === "pending").map((section) => (
            <Route
              key={section.key}
              path={section.path}
              element={<PendingLoopPage sectionKey={section.key} />}
            />
          ))}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AppShell>
    </TelemetryProvider>
  )
}
