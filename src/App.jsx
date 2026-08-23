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
import OrganizationsPage from "@/pages/admin/OrganizationsPage"
import SubscriptionsPlansPage from "@/pages/admin/SubscriptionsPlansPage"
import UsagePage from "@/pages/admin/UsagePage"
import FeatureFlagsPage from "@/pages/admin/FeatureFlagsPage"
import UsersPage from "@/pages/admin/UsersPage"

import SwipeFilesPage from "@/pages/SwipeFilesPage"
import BillingPage from "@/pages/BillingPage"
import ApiKeysPage from "@/pages/ApiKeysPage"
import TeamPage from "@/pages/TeamPage"

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
  "/swipe-files": "Swipe Files",
  "/billing": "Billing & Usage",
  "/api-keys": "API Keys",
  "/team": "Team Members",
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

export default function App() {
  return (
    <TelemetryProvider>
      <AuthProvider>
        <DocumentTitle />
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
              <Route path="/admin/organizations" element={<OrganizationsPage />} />
              <Route path="/admin/subscriptions" element={<SubscriptionsPlansPage />} />
              <Route path="/admin/usage" element={<UsagePage />} />
              <Route path="/admin/feature-flags" element={<FeatureFlagsPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
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
              <Route path="/swipe-files" element={<SwipeFilesPage />} />
              <Route path="/billing" element={<BillingPage />} />
              <Route path="/api-keys" element={<ApiKeysPage />} />
              <Route path="/team" element={<TeamPage />} />
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
