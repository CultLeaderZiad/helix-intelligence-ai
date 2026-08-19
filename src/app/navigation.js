import { Radar, Network, PenLine, Activity } from "lucide-react"

/**
 * The four loops of the product. Single source of truth for the sidebar,
 * the command bar, and the document title — so a route can never appear
 * in one navigation surface and be missing from another.
 */
export const NAV_SECTIONS = [
  {
    key: "discover",
    path: "/discover",
    label: "Discover",
    icon: Radar,
    description: "Query competitor ad libraries and rank what is running.",
    status: "live",
  },
  {
    key: "intelligence",
    path: "/intelligence",
    label: "Intelligence",
    icon: Network,
    description: "Mine recurring patterns across a discovered corpus.",
    status: "pending",
  },
  {
    key: "create",
    path: "/create",
    label: "Create",
    icon: PenLine,
    description: "Draft new creative briefed on the patterns that win.",
    status: "pending",
  },
  {
    key: "performance",
    path: "/performance",
    label: "Performance",
    icon: Activity,
    description: "Feed live outcomes back into the scoring model.",
    status: "pending",
  },
]
