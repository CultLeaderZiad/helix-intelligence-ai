import { Link } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState } from "@/components/ui/States"
import { NAV_SECTIONS } from "@/app/navigation"

/**
 * Placeholder surface for the loops that have no data source yet.
 *
 * It states plainly that the loop is unbuilt rather than faking a
 * dashboard — a fake screen here would be indistinguishable from a
 * finished one during review.
 */
export function PendingLoopPage({ sectionKey }) {
  const section = NAV_SECTIONS.find((s) => s.key === sectionKey)
  if (!section) return null

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <BreadcrumbBar trail={["Helix", section.label]} meta="no source connected" />
      <EmptyState
        icon={section.icon}
        title={`${section.label} is not wired up yet`}
        description={section.description}
        action={
          <Button as={Link} to="/discover" size="sm" variant="outline">
            Back to Discover
          </Button>
        }
      />
    </div>
  )
}

export default PendingLoopPage
