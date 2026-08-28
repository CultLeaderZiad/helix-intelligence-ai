import { lazy, Suspense, useEffect } from "react"
import { Outlet, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { AdminShell } from "@/app/admin/AdminShell"
import { ProtectedRoute } from "@/app/ProtectedRoute"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { ADMIN_NAV_ITEMS } from "@/app/admin/adminNavigation"
import { AuthProvider } from "@/context/AuthContext"
import { LandingPage } from "@/pages/LandingPage"

// ── Lazy-loaded page chunks ──────────────────────────────────────
// Each dynamic import becomes a separate Vite chunk, loaded only
// when the user navigates to that route.
// Components with named exports need { default: X } wrappers.
const SignInPage = lazy(() => import("@/pages/auth/SignInPage").then(m => ({ default: m.SignInPage })))
const SignUpPage = lazy(() => import("@/pages/auth/SignUpPage").then(m => ({ default: m.SignUpPage })))
const ForgotPasswordPage = lazy(() => import("@/pages/auth/ForgotPasswordPage").then(m => ({ default: m.ForgotPasswordPage })))
const DiscoverPage = lazy(() => import("@/pages/DiscoverPage").then(m => ({ default: m.DiscoverPage })))
const PendingLoopPage = lazy(() => import("@/pages/PendingLoopPage").then(m => ({ default: m.PendingLoopPage })))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })))
const SwipeFilesPage = lazy(() => import("@/pages/SwipeFilesPage"))
const CreatePage = lazy(() => import("@/pages/CreatePage"))
const BillingPage = lazy(() => import("@/pages/BillingPage"))
const ApiKeysPage = lazy(() => import("@/pages/ApiKeysPage"))
const TeamPage = lazy(() => import("@/pages/TeamPage"))
const OverviewPage = lazy(() => import("@/pages/admin/OverviewPage").then(m => ({ default: m.OverviewPage })))
const AdminPendingPage = lazy(() => import("@/pages/admin/AdminPendingPage").then(m => ({ default: m.AdminPendingPage })))
const OrganizationsPage = lazy(() => import("@/pages/admin/OrganizationsPage"))
const SubscriptionsPlansPage = lazy(() => import("@/pages/admin/SubscriptionsPlansPage"))
const UsagePage = lazy(() => import("@/pages/admin/UsagePage"))
const FeatureFlagsPage = lazy(() => import("@/pages/admin/FeatureFlagsPage"))
const UsersPage = lazy(() => import("@/pages/admin/UsersPage"))
const UpdatesPage = lazy(() => import("@/pages/admin/UpdatesPage"))

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

function PageLoader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#888', fontFamily: 'system-ui' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
        <div>Loading…</div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <TelemetryProvider>
      <AuthProvider>
        <DocumentTitle />
        <Suspense fallback={<PageLoader />}>
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
              <Route path="/admin/updates" element={<UpdatesPage />} />
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
              <Route path="/create" element={<CreatePage />} />
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
        </Suspense>
      </AuthProvider>
    </TelemetryProvider>
  )
}
