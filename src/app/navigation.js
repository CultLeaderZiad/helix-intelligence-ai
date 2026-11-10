import { Radar, Eye, Bookmark } from "lucide-react"

/**
 * The loops of the product. Single source of truth for the sidebar,
 * the command bar, and the document title — so a route can never appear
 * in one navigation surface and be missing from another.
 *
 * `feature` is the per-workspace flag that the backend enforces for the
 * section's API (require_feature). Discover is always listed: its page
 * explains how to request access when the workspace is not granted it.
 */
export const NAV_SECTIONS = [
  {
    key: "discover",
    path: "/discover",
    label: "Discover",
    icon: Radar,
    feature: null,
    description: "Query competitor ad libraries and rank what is running.",
    status: "live",
  },
  {
    key: "monitors",
    path: "/monitors",
    label: "Monitors",
    icon: Eye,
    feature: "monitors",
    description: "Re-run a search on a schedule and report what changed.",
    status: "live",
  },
  {
    key: "swipeFiles",
    path: "/swipe-files",
    label: "Swipe Files",
    icon: Bookmark,
    feature: "swipe_files",
    description: "Save ads into boards and share a report.",
    status: "live",
  },
]

/** @param {string | null | undefined} feature @param {Record<string, boolean> | null | undefined} flags */
export function hasFeature(feature, flags) {
  return !feature || flags?.[feature] === true
}

/** Sections the signed-in workspace is granted. */
export function visibleSections(flags) {
  return NAV_SECTIONS.filter((section) => hasFeature(section.feature, flags))
}
