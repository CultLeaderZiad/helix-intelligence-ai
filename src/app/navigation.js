import { EXPERIMENTAL_FEATURES_ENABLED } from "@/lib/productFeatures"
import { Radar, Eye } from "lucide-react"

/**
 * The loops of the product. Single source of truth for the sidebar,
 * the command bar, and the document title — so a route can never appear
 * in one navigation surface and be missing from another.
 */
const ALL_SECTIONS = [
  {
    key: "discover",
    path: "/discover",
    label: "Discover",
    icon: Radar,
    description: "Query competitor ad libraries and rank what is running.",
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
]

export const NAV_SECTIONS = ALL_SECTIONS.filter((section) => section.key === "discover" || EXPERIMENTAL_FEATURES_ENABLED)
