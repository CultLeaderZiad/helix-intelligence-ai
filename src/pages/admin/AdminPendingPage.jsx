import { Link } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState } from "@/components/ui/States"
import { ADMIN_NAV_ITEMS } from "@/app/admin/adminNavigation"

/**
 * Placeholder for admin surfaces that have no backend yet. Mirrors the
 * customer app's PendingLoopPage: it states plainly that the surface is
 * unbuilt rather than faking an operations screen, because a fake console
 * is indistinguishable from a finished one during review.
 */
export function AdminPendingPage({ itemKey }) {
  const item = ADMIN_NAV_ITEMS.find((i) => i.key === itemKey)
  if (!item) return null

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <BreadcrumbBar trail={["Console", item.label]} meta="not implemented" />
      <EmptyState
        icon={item.icon}
        title={`${item.label} is not wired up yet`}
        description="This console surface is scaffolded in navigation but has no data source connected in this pass. The Overview dashboard is the built surface."
        action={
          <Button as={Link} to="/admin" size="sm" variant="outline">
            Back to Dashboard
          </Button>
        }
      />
    </div>
  )
}

export default AdminPendingPage
