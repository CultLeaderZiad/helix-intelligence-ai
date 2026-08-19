import { useEffect } from "react"
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { ProtectedRoute } from "@/app/ProtectedRoute"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { AuthProvider } from "@/context/AuthContext"
import { DiscoverPage } from "@/pages/DiscoverPage"
import { PendingLoopPage } from "@/pages/PendingLoopPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage"
import { SignInPage } from "@/pages/auth/SignInPage"
import { SignUpPage } from "@/pages/auth/SignUpPage"

/**
 * Root component. Deliberately thin: it mounts shell-level providers,
 * the chrome, and the route table — nothing else. `BrowserRouter` lives
 * in main.jsx so this component stays testable without a router mock.
 *
 * Routes are derived from NAV_SECTIONS so a loop can never exist in the
 * sidebar without a matching route.
 */
const PUBLIC_TITLES = {
  "/sign-in": "Sign in",
  "/sign-up": "Create account",
  "/forgot-password": "Reset password",
}

function DocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const section = NAV_SECTIONS.find((s) => pathname.startsWith(s.path))
    const label = PUBLIC_TITLES[pathname] ?? section?.label
    document.title = label ? `${label} · Helix Intelligence` : "Helix Intelligence"
  }, [pathname])

  return null
}

function AuthenticatedShell() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}

export default function App() {
  return (
    <TelemetryProvider>
      <AuthProvider>
        <DocumentTitle />
        <Routes>
          <Route path="/sign-in" element={<SignInPage />} />
          <Route path="/sign-up" element={<SignUpPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AuthenticatedShell />}>
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
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </TelemetryProvider>
  )
}
