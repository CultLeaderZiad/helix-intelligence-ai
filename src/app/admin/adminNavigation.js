import { EXPERIMENTAL_FEATURES_ENABLED } from "@/lib/productFeatures"
import {
  LayoutDashboard,
  Building2,
  Users,
  CreditCard,
  Gauge,
  Database,
  ListChecks,
  HeartPulse,
  Flag,
  ScrollText,
  Bell,
  BookOpen,
  MessageSquareCheck,
  ShieldCheck,
} from "lucide-react"

/**
 * The admin console's rail. Single source of truth for the sidebar, the
 * route table, and the document title.
 */
export const ADMIN_HOME = "/admin"

const ALL_ADMIN_NAV_GROUPS = [
  {
    label: "Overview",
    items: [
      {
        key: "dashboard",
        path: "/admin",
        label: "Dashboard",
        icon: LayoutDashboard,
        end: true,
        built: true,
      },
      {
        key: "admin-guide",
        path: "/admin/guide",
        label: "Operating Playbook",
        icon: BookOpen,
        built: true,
      },
    ],
  },
  {
    label: "Accounts",
    items: [
      {
        key: "organizations",
        path: "/admin/organizations",
        label: "Organizations",
        icon: Building2,
        built: true,
      },
      {
        key: "access-requests",
        path: "/admin/access-requests",
        label: "Access Requests",
        icon: ShieldCheck,
        built: true,
      },
      {
        key: "users",
        path: "/admin/users",
        label: "Users",
        icon: Users,
        built: true,
      },
      {
        key: "support",
        path: "/admin/support",
        label: "Support Tickets",
        icon: MessageSquareCheck,
        built: true,
      },
    ],
  },
  {
    label: "Billing",
    items: [
      {
        key: "subscriptions",
        path: "/admin/subscriptions",
        label: "Subscriptions & Plans",
        icon: CreditCard,
        built: true,
      },
      {
        key: "usage",
        path: "/admin/usage",
        label: "Usage & Metering",
        icon: Gauge,
        built: true,
      },
    ],
  },
  {
    label: "Data",
    items: [
      {
        key: "data-sources",
        path: "/admin/data-sources",
        label: "Data Sources",
        icon: Database,
        built: true,
      },
      {
        key: "scrape-jobs",
        path: "/admin/scrape-jobs",
        label: "Scrape Jobs",
        icon: ListChecks,
        built: true,
      },
    ],
  },
  {
    label: "System",
    items: [
      {
        key: "updates",
        path: "/admin/updates",
        label: "Updates & Banners",
        icon: Bell,
        built: true,
      },
      {
        key: "health",
        path: "/admin/health",
        label: "Health",
        icon: HeartPulse,
        built: true,
      },
      {
        key: "feature-flags",
        path: "/admin/feature-flags",
        label: "Feature Flags",
        icon: Flag,
        built: true,
      },
      {
        key: "audit-log",
        path: "/admin/audit-log",
        label: "Audit Log",
        icon: ScrollText,
        built: true,
      },
    ],
  },
]

/** Flattened lookup for routing and the document title. */
export const ADMIN_NAV_GROUPS = ALL_ADMIN_NAV_GROUPS.map((group) => ({ ...group, items: group.items.filter((item) => EXPERIMENTAL_FEATURES_ENABLED || !["admin-guide", "subscriptions", "usage", "data-sources", "scrape-jobs", "feature-flags", "health"].includes(item.key)) })).filter((group) => group.items.length > 0)

export const ADMIN_NAV_ITEMS = ADMIN_NAV_GROUPS.flatMap((g) => g.items)
