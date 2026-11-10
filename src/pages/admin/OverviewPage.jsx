import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { Panel, PanelHeader, PanelTitle } from "@/components/ui/Panel"
import { ErrorState, Skeleton } from "@/components/ui/States"
import { Tag } from "@/components/ui/Tag"
import { OverviewStatStrip } from "@/features/admin/OverviewStatStrip"
import { RecentJobsTable } from "@/features/admin/RecentJobsTable"
import { SystemHealthPanel } from "@/features/admin/SystemHealthPanel"
import { OrganizationsTable } from "@/features/admin/OrganizationsTable"
import { UsersTable } from "@/features/admin/UsersTable"
import { useAdminOverview } from "@/hooks/useAdminOverview"
import { useLanguage } from "@/context/LanguageContext"
import { adminMessage, adminStatusLabel } from "@/i18n/adminMessages"

/**
 * ============================================================
 * ADMIN OVERVIEW — the one fully-built console surface
 * ============================================================
 * Composition root for the operations dashboard. It owns no data: every
 * figure comes from `useAdminOverview`, the single route to the admin
 * service. The three panels load, fail, and retry as one unit so the
 * screen is never half-true.
 * ============================================================
 */
export function OverviewPage() {
  const { lang, isRtl } = useLanguage()
  const { stats, jobs, health, organizations, users, loading, error, refetch } = useAdminOverview()

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="w-full flex-1 flex flex-col font-sans">
      <BreadcrumbBar
        trail={[adminMessage(lang, "Console"), adminMessage(lang, "Overview")]}
        meta={adminMessage(lang, loading ? "Loading" : error ? "Unavailable" : "Live")}
        actions={
          <Button size="xs" variant="ghost" onClick={refetch} disabled={loading}>
            {adminMessage(lang, "Refresh")}
          </Button>
        }
      />

      {error ? (
        <ErrorState className="" description={adminMessage(lang, "Admin overview metrics could not be loaded. Retry to reload them.")} error={error} onRetry={refetch} />
      ) : (
        <div className="p-3 md:p-6 w-full">
          <div className="mx-auto flex max-w-7xl flex-col gap-4">
            {loading || !stats ? (
              <Skeleton className="h-[92px] w-full rounded-sm" />
            ) : (
              <OverviewStatStrip stats={stats} />
            )}

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
              <Panel className="flex min-w-0 flex-col lg:col-span-2">
                <PanelHeader>
                  <PanelTitle>{adminMessage(lang, "Recent scrape jobs")}</PanelTitle>
                  {!loading && jobs.length ? (
                    <Tag className="">{adminMessage(lang, "{count} shown", { count: jobs.length })}</Tag>
                  ) : null}
                </PanelHeader>
                {loading ? (
                  <JobsSkeleton />
                ) : (
                  <RecentJobsTable jobs={jobs} />
                )}
              </Panel>

              <Panel className="flex min-w-0 flex-col">
                <PanelHeader>
                  <PanelTitle>{adminMessage(lang, "System health")}</PanelTitle>
                  {!loading && health ? (
                    <Tag className="" tone={HEALTH_TAG_TONE[health.state] ?? "default"}>
                      {adminStatusLabel(lang, health.state)}
                    </Tag>
                  ) : null}
                </PanelHeader>
                {loading || !health ? (
                  <HealthSkeleton />
                ) : (
                  <SystemHealthPanel services={health.services} />
                )}
              </Panel>
            </div>

            <Panel className="flex min-w-0 flex-col">
              <PanelHeader>
                <PanelTitle>{adminMessage(lang, "Organizations")}</PanelTitle>
                {!loading && organizations?.length ? (
                  <Tag className="">{adminMessage(lang, "{count} total", { count: organizations.length })}</Tag>
                ) : null}
              </PanelHeader>
              {loading ? (
                <JobsSkeleton />
              ) : (
                <OrganizationsTable organizations={organizations} onRefresh={refetch} />
              )}
            </Panel>

            <Panel className="flex min-w-0 flex-col">
              <PanelHeader>
                <PanelTitle>{adminMessage(lang, "Users")}</PanelTitle>
                {!loading && users?.length ? (
                  <Tag className="">{adminMessage(lang, "{count} total", { count: users.length })}</Tag>
                ) : null}
              </PanelHeader>
              {loading ? (
                <JobsSkeleton />
              ) : (
                <UsersTable users={users} onRefresh={refetch} />
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  )
}

const HEALTH_TAG_TONE = {
  operational: "success",
  degraded: "warning",
  down: "danger",
}

/** Row-shaped skeletons that mirror each panel so nothing reflows in. */
function JobsSkeleton() {
  return (
    <div className="flex flex-col" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-2.5"
          style={{ opacity: Math.max(0.2, 1 - i * 0.12) }}
        >
          <Skeleton className="h-3 w-16 shrink-0" />
          <Skeleton className="h-3 w-28 shrink-0" />
          <Skeleton className="h-3 flex-1" />
          <Skeleton className="h-4 w-14 shrink-0" />
        </div>
      ))}
    </div>
  )
}

function HealthSkeleton() {
  return (
    <div className="flex flex-col" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5">
          <Skeleton className="h-2 w-2 shrink-0 rounded-full" />
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3 w-[40%]" />
            <Skeleton className="h-2 w-[60%]" />
          </div>
          <Skeleton className="h-3 w-10 shrink-0" />
        </div>
      ))}
    </div>
  )
}

export default OverviewPage
