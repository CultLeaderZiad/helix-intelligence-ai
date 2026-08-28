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
} from "lucide-react"

/**
 * The admin console's rail. Single source of truth for the sidebar, the
 * route table, and the document title — the same discipline NAV_SECTIONS
 * enforces for the customer app, so an admin route can never appear in
 * one surface and be missing from another.
 *
 * `built` marks which surfaces have a real implementation this pass.
 * Everything else routes to a placeholder rather than a faked screen.
 * Groups render with the `// LABEL` monospace treatment.
 */
export const ADMIN_HOME = "/admin"

export const ADMIN_NAV_GROUPS = [
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
        key: "users",
        path: "/admin/users",
        label: "Users",
        icon: Users,
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
        built: false,
      },
      {
        key: "scrape-jobs",
        path: "/admin/scrape-jobs",
        label: "Scrape Jobs",
        icon: ListChecks,
        built: false,
      },
    ],
  },
  {
    label: "System",
    items: [
      {
        key: "health",
        path: "/admin/health",
        label: "Health",
        icon: HeartPulse,
        built: false,
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
        built: false,
      },
    ],
  },
]

/** Flattened lookup for routing and the document title. */
export const ADMIN_NAV_ITEMS = ADMIN_NAV_GROUPS.flatMap((g) => g.items)
