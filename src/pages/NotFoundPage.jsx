import { Link, useLocation } from "react-router-dom"
import { FileQuestion } from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import { EmptyState } from "@/components/ui/States"

export function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <BreadcrumbBar trail={["Helix", "Not found"]} meta={pathname} />
      <EmptyState
        icon={FileQuestion}
        title="No surface at this route"
        description="The path does not map to any loop in the product. Navigation is driven by a single route table, so this is a typed URL rather than a broken link."
        action={
          <Button as={Link} to="/discover" size="sm" variant="outline">
            Go to Discover
          </Button>
        }
      />
    </div>
  )
}

export default NotFoundPage
