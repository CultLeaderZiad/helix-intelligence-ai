import { useEffect } from "react"
import { Outlet, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { AdminShell } from "@/app/admin/AdminShell"
import { ProtectedRoute } from "@/app/ProtectedRoute"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { ADMIN_NAV_ITEMS } from "@/app/admin/adminNavigation"
import { AuthProvider } from "@/context/AuthContext"
import { LandingPage } from "@/pages/LandingPage"
import { DiscoverPage } from "@/pages/DiscoverPage"
import { PendingLoopPage } from "@/pages/PendingLoopPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage"
import { SignInPage } from "@/pages/auth/SignInPage"
import { SignUpPage } from "@/pages/auth/SignUpPage"
import { OverviewPage } from "@/pages/admin/OverviewPage"
import { AdminPendingPage } from "@/pages/admin/AdminPendingPage"

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
    // Longest-match so /admin/organizations beats /admin before "/".
    const adminItem = [...ADMIN_NAV_ITEMS]
      .sort((a, b) => b.path.length - a.path.length)
      .find((i) => pathname === i.path || pathname.startsWith(`${i.path}/`))
    const section = NAV_SECTIONS.find((s) => pathname.startsWith(s.path))
    const label = PUBLIC_TITLES[pathname] ?? adminItem?.label ?? section?.label
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

function AdminShellLayout() {
  return (
    <AdminShell>
      <Outlet />
    </AdminShell>
  )
}

function ScrollToHash() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (hash) {
      const id = hash.slice(1)
      const scroll = () => {
        const element = document.getElementById(id)
        if (element) {
          element.scrollIntoView({ behavior: "smooth" })
        }
      }
      scroll()
      // Fallback for DOM changes / loading delay
      const timer = setTimeout(scroll, 100)
      return () => clearTimeout(timer)
    } else {
      window.scrollTo(0, 0)
    }
  }, [pathname, hash])

  return null
}

export default function App() {
  return (
    <TelemetryProvider>
      <AuthProvider>
        <DocumentTitle />
        <ScrollToHash />
        <Routes>
          {/* Public front door. Fully ungated — the marketing surface the
              header nav points at. Auth pages are reached only by choice. */}
          <Route path="/" element={<LandingPage />} />

          <Route path="/sign-in" element={<SignInPage />} />
          <Route path="/sign-up" element={<SignUpPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />

          {/* Admin console — admin role only; customers bounce to APP_HOME. */}
          <Route element={<ProtectedRoute requireRole="admin" />}>
            <Route element={<AdminShellLayout />}>
              <Route path="/admin" element={<OverviewPage />} />
              {ADMIN_NAV_ITEMS.filter((i) => !i.built).map((item) => (
                <Route
                  key={item.key}
                  path={item.path}
                  element={<AdminPendingPage itemKey={item.key} />}
                />
              ))}
            </Route>
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<AuthenticatedShell />}>
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
