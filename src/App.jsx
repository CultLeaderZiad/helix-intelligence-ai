import { lazy, Suspense, useEffect } from "react"
import { Outlet, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { AdminShell } from "@/app/admin/AdminShell"
import { ProtectedRoute } from "@/app/ProtectedRoute"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { ADMIN_NAV_ITEMS } from "@/app/admin/adminNavigation"
import { AuthProvider } from "@/context/AuthContext"
import { SearchProvider } from "@/context/SearchContext"
import { LanguageProvider } from "@/context/LanguageContext"
import { LandingPage } from "@/pages/LandingPage"
import { ErrorBoundary } from "@/components/ErrorBoundary"

// Lazy loaded pages with robust named export mapping
const SignInPage = lazy(() => import("@/pages/auth/SignInPage").then(m => ({ default: m.SignInPage })))
const SignUpPage = lazy(() => import("@/pages/auth/SignUpPage").then(m => ({ default: m.SignUpPage })))
const ForgotPasswordPage = lazy(() => import("@/pages/auth/ForgotPasswordPage").then(m => ({ default: m.ForgotPasswordPage })))
const DiscoverPage = lazy(() => import("@/pages/DiscoverPage").then(m => ({ default: m.DiscoverPage })))
const IntelligencePage = lazy(() => import("@/pages/IntelligencePage").then(m => ({ default: m.IntelligencePage })))
const PerformancePage = lazy(() => import("./pages/PerformancePage").then(m => ({ default: m.default || m.PerformancePage })))
const DashboardPage = lazy(() => import("./pages/DashboardPage").then(m => ({ default: m.default || m.DashboardPage })))
const CreatePage = lazy(() => import("@/pages/CreatePage").then(m => ({ default: m.CreatePage })))
const GuidePage = lazy(() => import("@/pages/GuidePage").then(m => ({ default: m.GuidePage })))
const SwipeFilesPage = lazy(() => import("@/pages/SwipeFilesPage").then(m => ({ default: m.SwipeFilesPage })))
const BillingPage = lazy(() => import("@/pages/BillingPage").then(m => ({ default: m.BillingPage })))
const ApiKeysPage = lazy(() => import("@/pages/ApiKeysPage").then(m => ({ default: m.ApiKeysPage })))
const TeamPage = lazy(() => import("@/pages/TeamPage").then(m => ({ default: m.TeamPage })))
const PendingLoopPage = lazy(() => import("@/pages/PendingLoopPage").then(m => ({ default: m.PendingLoopPage })))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })))
const OverviewPage = lazy(() => import("@/pages/admin/OverviewPage").then(m => ({ default: m.OverviewPage })))
const AdminPendingPage = lazy(() => import("@/pages/admin/AdminPendingPage").then(m => ({ default: m.AdminPendingPage })))
const OrganizationsPage = lazy(() => import("@/pages/admin/OrganizationsPage").then(m => ({ default: m.OrganizationsPage })))
const SubscriptionsPlansPage = lazy(() => import("@/pages/admin/SubscriptionsPlansPage").then(m => ({ default: m.SubscriptionsPlansPage })))
const UsagePage = lazy(() => import("@/pages/admin/UsagePage").then(m => ({ default: m.UsagePage })))
const FeatureFlagsPage = lazy(() => import("@/pages/admin/FeatureFlagsPage").then(m => ({ default: m.FeatureFlagsPage })))
const UsersPage = lazy(() => import("@/pages/admin/UsersPage").then(m => ({ default: m.UsersPage })))
const UpdatesPage = lazy(() => import("@/pages/admin/UpdatesPage").then(m => ({ default: m.UpdatesPage })))
const SupportAdminPage = lazy(() => import("@/pages/admin/SupportAdminPage").then(m => ({ default: m.SupportAdminPage })))
const PublicPlaybookPage = lazy(() => import("@/pages/PublicPlaybookPage").then(m => ({ default: m.PublicPlaybookPage })))
const ProfileSettingsPage = lazy(() => import("@/pages/ProfileSettingsPage").then(m => ({ default: m.ProfileSettingsPage })))
const SupportPage = lazy(() => import("@/pages/SupportPage").then(m => ({ default: m.SupportPage })))
const NotificationsPage = lazy(() => import("@/pages/NotificationsPage").then(m => ({ default: m.NotificationsPage })))

const PUBLIC_TITLES = {
  "/sign-in": "Sign in",
  "/sign-up": "Create account",
  "/forgot-password": "Reset password",
  "/swipe-files": "Swipe Files",
  "/guide": "Playbook & Guide",
  "/intelligence": "Intelligence & Patterns",
  "/performance": "Performance & Fatigue",
  "/billing": "Billing & Usage",
  "/api-keys": "API Keys",
  "/team": "Team Members",
  "/settings": "Profile & Settings",
  "/support": "Support & Feedback",
  "/notifications": "Notifications & Announcements",
}

function DocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
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
    <ErrorBoundary>
      <TelemetryProvider>
        <LanguageProvider>
          <AuthProvider>
            <SearchProvider>
              <DocumentTitle />
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  {/* Public front door */}
                  <Route path="/" element={<LandingPage />} />

                  <Route path="/sign-in" element={<SignInPage />} />
                  <Route path="/sign-up" element={<SignUpPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                  <Route path="/playbook/:publicId" element={<PublicPlaybookPage />} />

                  {/* Admin console — admin role only */}
                  <Route element={<ProtectedRoute requireRole="admin" />}>
                    <Route element={<AdminShellLayout />}>
                      <Route path="/admin" element={<OverviewPage />} />
                      <Route path="/admin/guide" element={<GuidePage />} />
                      <Route path="/admin/organizations" element={<OrganizationsPage />} />
                      <Route path="/admin/subscriptions" element={<SubscriptionsPlansPage />} />
                      <Route path="/admin/usage" element={<UsagePage />} />
                      <Route path="/admin/feature-flags" element={<FeatureFlagsPage />} />
                      <Route path="/admin/users" element={<UsersPage />} />
                      <Route path="/admin/updates" element={<UpdatesPage />} />
                      <Route path="/admin/support" element={<SupportAdminPage />} />
                      {ADMIN_NAV_ITEMS.filter((i) => !i.built).map((item) => (
                        <Route
                          key={item.key}
                          path={item.path}
                          element={<AdminPendingPage itemKey={item.key} />}
                        />
                      ))}
                    </Route>
                  </Route>

                  {/* Customer authenticated app */}
                  <Route element={<ProtectedRoute />}>
                    <Route element={<AuthenticatedShell />}>
                      <Route path="/discover" element={<DiscoverPage />} />
                      <Route path="/intelligence" element={<IntelligencePage />} />
                      <Route path="/create" element={<CreatePage />} />
                      <Route path="performance" element={<PerformancePage />} />
                      <Route path="dashboard" element={<DashboardPage />} />
                      <Route path="/swipe-files" element={<SwipeFilesPage />} />
                      <Route path="/guide" element={<GuidePage />} />
                      <Route path="/billing" element={<BillingPage />} />
                      <Route path="/api-keys" element={<ApiKeysPage />} />
                      <Route path="/team" element={<TeamPage />} />
                      <Route path="/settings" element={<ProfileSettingsPage />} />
                      <Route path="/support" element={<SupportPage />} />
                      <Route path="/notifications" element={<NotificationsPage />} />
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
            </SearchProvider>
          </AuthProvider>
        </LanguageProvider>
      </TelemetryProvider>
    </ErrorBoundary>
  )
}
