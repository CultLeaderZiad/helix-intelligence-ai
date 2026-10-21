import { EXPERIMENTAL_FEATURES_ENABLED } from "@/lib/productFeatures"
import { lazy, Suspense, useEffect } from "react"
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/app/AppShell"
import { ProtectedRoute } from "@/app/ProtectedRoute"
import { TelemetryProvider } from "@/app/TelemetryContext"
import { NAV_SECTIONS } from "@/app/navigation"
import { ADMIN_NAV_ITEMS } from "@/app/admin/adminNavigation"
import { AuthProvider } from "@/context/AuthContext"
import { SearchProvider } from "@/context/SearchContext"
import { LanguageProvider } from "@/context/LanguageContext"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { trackPageview } from "@/lib/analytics"
import { captureAttribution } from "@/lib/utm"

// Safe lazy-loading with automatic auto-reload on stale deployment chunks
function safeLazy(importFn) {
  return lazy(async () => {
    try {
      return await importFn()
    } catch (err) {
      console.warn("A lazy-loaded module failed to load.")
      let lastReload
      try {
        lastReload = Number(window.sessionStorage.getItem("chunk_reload_lock") || 0)
      } catch {
        throw err
      }
      const now = Date.now()
      if (now - lastReload > 8000) {
        try {
          window.sessionStorage.setItem("chunk_reload_lock", String(now))
        } catch {
          throw err
        }
        window.location.reload()
        return new Promise(() => {})
      }
      throw err
    }
  })
}

const LandingPage = safeLazy(() => import("@/pages/LandingPage").then(m => ({ default: m.LandingPage })))
const AdminShell = safeLazy(() => import("@/app/admin/AdminShell").then(m => ({ default: m.AdminShell })))

// Lazy loaded pages with robust named export mapping
const SignInPage = safeLazy(() => import("@/pages/auth/SignInPage").then(m => ({ default: m.SignInPage })))
const SignUpPage = safeLazy(() => import("@/pages/auth/SignUpPage").then(m => ({ default: m.SignUpPage })))
const ForgotPasswordPage = safeLazy(() => import("@/pages/auth/ForgotPasswordPage").then(m => ({ default: m.ForgotPasswordPage })))
const ResetPasswordPage = safeLazy(() => import("@/pages/auth/ResetPasswordPage").then(m => ({ default: m.ResetPasswordPage })))
const DiscoverPage = safeLazy(() => import("@/pages/DiscoverPage").then(m => ({ default: m.DiscoverPage })))
const IntelligencePage = safeLazy(() => import("@/pages/IntelligencePage").then(m => ({ default: m.IntelligencePage })))
const PerformancePage = safeLazy(() => import("./pages/PerformancePage").then(m => ({ default: m.default || m.PerformancePage })))
const optionalPage = (page) => EXPERIMENTAL_FEATURES_ENABLED ? page : <Navigate to="/discover" replace />

const DashboardPage = safeLazy(() => import("./pages/DashboardPage").then(m => ({ default: m.default })))
const CreatePage = safeLazy(() => import("@/pages/CreatePage").then(m => ({ default: m.CreatePage })))
const MonitorsPage = safeLazy(() => import("@/pages/MonitorsPage").then(m => ({ default: m.MonitorsPage })))
const GuidePage = safeLazy(() => import("@/pages/GuidePage").then(m => ({ default: m.GuidePage })))
const SwipeFilesPage = safeLazy(() => import("@/pages/SwipeFilesPage").then(m => ({ default: m.SwipeFilesPage })))
const BillingPage = safeLazy(() => import("@/pages/BillingPage").then(m => ({ default: m.BillingPage })))
const ApiKeysPage = safeLazy(() => import("@/pages/ApiKeysPage").then(m => ({ default: m.ApiKeysPage })))
const TeamPage = safeLazy(() => import("@/pages/TeamPage").then(m => ({ default: m.TeamPage })))
const TeamAcceptPage = safeLazy(() => import("@/pages/TeamPage").then(m => ({ default: m.TeamAcceptPage })))
const PendingLoopPage = safeLazy(() => import("@/pages/PendingLoopPage").then(m => ({ default: m.PendingLoopPage })))
const NotFoundPage = safeLazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })))
const OverviewPage = safeLazy(() => import("@/pages/admin/OverviewPage").then(m => ({ default: m.OverviewPage })))
const AdminPendingPage = safeLazy(() => import("@/pages/admin/AdminPendingPage").then(m => ({ default: m.AdminPendingPage })))
const OrganizationsPage = safeLazy(() => import("@/pages/admin/OrganizationsPage").then(m => ({ default: m.OrganizationsPage })))
const AccessRequestsPage = safeLazy(() => import("@/pages/admin/AccessRequestsPage").then(m => ({ default: m.AccessRequestsPage })))
const SubscriptionsPlansPage = safeLazy(() => import("@/pages/admin/SubscriptionsPlansPage").then(m => ({ default: m.SubscriptionsPlansPage })))
const UsagePage = safeLazy(() => import("@/pages/admin/UsagePage").then(m => ({ default: m.UsagePage })))
const FeatureFlagsPage = safeLazy(() => import("@/pages/admin/FeatureFlagsPage").then(m => ({ default: m.FeatureFlagsPage })))
const UsersPage = safeLazy(() => import("@/pages/admin/UsersPage").then(m => ({ default: m.UsersPage })))
const UpdatesPage = safeLazy(() => import("@/pages/admin/UpdatesPage").then(m => ({ default: m.UpdatesPage })))
const SupportAdminPage = safeLazy(() => import("@/pages/admin/SupportAdminPage").then(m => ({ default: m.SupportAdminPage })))
const ScrapeJobsPage = safeLazy(() => import("@/pages/admin/ScrapeJobsPage").then(m => ({ default: m.ScrapeJobsPage })))
const DataSourcesPage = safeLazy(() => import("@/pages/admin/DataSourcesPage").then(m => ({ default: m.DataSourcesPage })))
const SystemHealthPage = safeLazy(() => import("@/pages/admin/SystemHealthPage").then(m => ({ default: m.SystemHealthPage })))
const AuditLogPage = safeLazy(() => import("@/pages/admin/AuditLogPage").then(m => ({ default: m.AuditLogPage })))
const PublicPlaybookPage = safeLazy(() => import("@/pages/PublicPlaybookPage").then(m => ({ default: m.PublicPlaybookPage })))
const PublicUpdatesPage = safeLazy(() => import("@/pages/PublicUpdatesPage").then(m => ({ default: m.PublicUpdatesPage })))
const ProfileSettingsPage = safeLazy(() => import("@/pages/ProfileSettingsPage").then(m => ({ default: m.ProfileSettingsPage })))
const SupportPage = safeLazy(() => import("@/pages/SupportPage").then(m => ({ default: m.SupportPage })))
const NotificationsPage = safeLazy(() => import("@/pages/NotificationsPage").then(m => ({ default: m.NotificationsPage })))
const DocsHomePage = safeLazy(() => import("@/pages/docs/DocsHomePage").then(m => ({ default: m.DocsHomePage })))
const DocsDetailPage = safeLazy(() => import("@/pages/docs/DocsDetailPage").then(m => ({ default: m.DocsDetailPage })))
const ScoutPage = safeLazy(() => import("@/pages/ScoutPage").then(m => ({ default: m.default || m.ScoutPage })))
const ScoutCliDocsPage = safeLazy(() => import("@/pages/docs/ScoutCliDocsPage").then(m => ({ default: m.default || m.ScoutCliDocsPage })))
const ScoutLeadGenerationPage = safeLazy(() => import("@/pages/ScoutLeadGenerationPage").then(m => ({ default: m.default || m.ScoutLeadGenerationPage })))
const LegalPage = safeLazy(() => import("@/pages/LegalPage").then(m => ({ default: m.LegalPage })))

const PUBLIC_TITLES = {
  "/docs": "Documentation & API Reference",
  "/privacy": "Privacy Policy",
  "/terms": "Terms of Service",
  "/cookies": "Cookie Policy",
  "/legal": "Legal Documents & Compliance",
  "/legal/subprocessors": "Authorized Sub-processors",
  "/sign-in": "Sign in",
  "/sign-up": "Create account",
  "/forgot-password": "Reset password",
  "/reset-password": "Set a new password",
  "/swipe-files": "Swipe Files",
  "/guide": "Playbook & Guide",
  "/scout/lead-generation": "Lead Generation",
  "/intelligence": "Intelligence & Patterns",
  "/performance": "Performance & Fatigue",
  "/billing": "Billing & Usage",
  "/api-keys": "API Keys",
  "/team": "Team Members",
  "/settings": "Profile & Settings",
  "/support": "Support & Feedback",
  "/notifications": "Notifications & Announcements",
  "/scout": "Scout · Social Lead Gen",
  "/docs/scout-cli": "Scout CLI Reference",
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

  // SPA pageview and UTM referral attribution capture on every route change
  useEffect(() => {
    captureAttribution()
    trackPageview(pathname)
  }, [pathname])

  return null
}

function AuthenticatedShell() {
  return (
    <AppShell>
      {/* Region boundary: a page-level crash shows a contained error while
          the shell (sidebar, nav, status bar) stays alive. */}
      <ErrorBoundary variant="region" label="This page">
        <Outlet />
      </ErrorBoundary>
    </AppShell>
  )
}

function AdminShellLayout() {
  return (
    <AdminShell>
      <ErrorBoundary variant="region" label="This admin page">
        <Outlet />
      </ErrorBoundary>
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
                  <Route path="/reset-password" element={<ResetPasswordPage />} />
                  <Route path="/playbook/:publicId" element={<PublicPlaybookPage />} />
                  <Route path="/updates" element={<PublicUpdatesPage />} />
                  <Route path="/legal" element={<LegalPage />} />
                  <Route path="/legal/:section" element={<LegalPage />} />
                  <Route path="/privacy" element={<LegalPage />} />
                  <Route path="/terms" element={<LegalPage />} />
                  <Route path="/cookies" element={<LegalPage />} />

                  {/* Public documentation system */}
                  <Route path="/docs" element={<DocsHomePage />} />
                  <Route path="/docs/scout-cli" element={<ScoutCliDocsPage />} />
                  <Route path="/docs/:section" element={<DocsDetailPage />} />
                  <Route path="/docs/:section/:slug" element={<DocsDetailPage />} />

                  {/* Admin console — admin role only */}
                  <Route element={<ProtectedRoute requireRole="admin" />}>
                    <Route element={<AdminShellLayout />}>
                      <Route path="/admin" element={<OverviewPage />} />
                      <Route path="/admin/guide" element={optionalPage(<GuidePage />)} />
                      <Route path="/admin/organizations" element={<OrganizationsPage />} />
                      <Route path="/admin/access-requests" element={<AccessRequestsPage />} />
                      <Route path="/admin/subscriptions" element={optionalPage(<SubscriptionsPlansPage />)} />
                      <Route path="/admin/usage" element={optionalPage(<UsagePage />)} />
                      <Route path="/admin/feature-flags" element={optionalPage(<FeatureFlagsPage />)} />
                      <Route path="/admin/users" element={<UsersPage />} />
                      <Route path="/admin/updates" element={<UpdatesPage />} />
                      <Route path="/admin/support" element={<SupportAdminPage />} />
                      <Route path="/admin/data-sources" element={optionalPage(<DataSourcesPage />)} />
                      <Route path="/admin/scrape-jobs" element={optionalPage(<ScrapeJobsPage />)} />
                      <Route path="/admin/health" element={optionalPage(<SystemHealthPage />)} />
                      <Route path="/admin/audit-log" element={<AuditLogPage />} />
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
                      <Route path="/intelligence" element={optionalPage(<IntelligencePage />)} />
                      <Route path="/create" element={optionalPage(<CreatePage />)} />
                      <Route path="/monitors" element={optionalPage(<MonitorsPage />)} />
                      <Route path="/scout" element={<Navigate to={EXPERIMENTAL_FEATURES_ENABLED ? "/scout/social" : "/discover"} replace />} />
                      <Route path="/scout/lead-generation" element={optionalPage(<ScoutLeadGenerationPage />)} />
                      <Route path="/scout/:mode" element={optionalPage(<ScoutPage />)} />
                      <Route path="performance" element={optionalPage(<PerformancePage />)} />
                      <Route path="dashboard" element={optionalPage(<DashboardPage />)} />
                      <Route path="/swipe-files" element={optionalPage(<SwipeFilesPage />)} />
                      <Route path="/guide" element={optionalPage(<GuidePage />)} />
                      <Route path="/access" element={<BillingPage />} />
                      <Route path="/billing" element={<Navigate to="/access" replace />} />
                      <Route path="/api-keys" element={optionalPage(<ApiKeysPage />)} />
                      <Route path="/team" element={optionalPage(<TeamPage />)} />
                      <Route path="/team/accept" element={optionalPage(<TeamAcceptPage />)} />
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
