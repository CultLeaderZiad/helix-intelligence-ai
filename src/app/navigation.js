import { Radar, Network, PenLine, Activity, BookOpen, Eye, Crosshair } from "lucide-react"

/**
 * The loops of the product. Single source of truth for the sidebar,
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
    status: "live",
  },
  {
    key: "create",
    path: "/create",
    label: "Create",
    icon: PenLine,
    description: "Draft new creative briefed on the patterns that win.",
    status: "live",
  },
  {
    key: "performance",
    path: "/performance",
    label: "Performance",
    icon: Activity,
    description: "Feed live outcomes back into the scoring model.",
    status: "live",
  },
  {
    key: "monitors",
    path: "/monitors",
    label: "Monitors",
    icon: Eye,
    description: "Re-run a search on a schedule and report what changed.",
    status: "live",
  },
  {
    key: "scout",
    path: "/scout",
    label: "Scout",
    icon: Crosshair,
    description: "Scrape social profiles, enrich contacts, export leads.",
    status: "live",
  },
]
