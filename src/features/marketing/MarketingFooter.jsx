import { Link } from "react-router-dom"
import { Logo } from "@/components/ui/Logo"

/**
 * Public footer. Same hairline/mono system as the rest of the site; the
 * columns re-list the section anchors and the two auth entry points so the
 * whole public surface is reachable from the bottom of the page too.
 */
const COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "Overview", path: "/#product" },
      { label: "Pricing", path: "/#pricing" },
      { label: "Docs", path: "/#docs" },
    ],
  },
]

export function MarketingFooter() {
  return (
    <footer className="border-t border-border bg-bg">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-12 md:flex-row md:items-start md:justify-between md:px-6">
        <div className="flex max-w-xs flex-col gap-3">
          <Logo />
          <p className="text-[13px] leading-relaxed text-text-muted">
            Competitive ad intelligence, instrumented. Discover, mine, brief, and
            measure — one loop at a time.
          </p>
        </div>

        <div className="flex flex-col gap-8 sm:flex-row sm:gap-16">
          {COLUMNS.map((column) => (
            <nav key={column.heading} className="flex flex-col gap-3" aria-label={column.heading}>
              <span className="label-mono">{column.heading}</span>
              <ul className="flex flex-col gap-2">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      to={link.path}
                      className="text-[13px] text-text-muted transition-colors hover:text-text"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          <nav className="flex flex-col gap-3" aria-label="Account">
            <span className="label-mono">Account</span>
            <ul className="flex flex-col gap-2">
              <li>
                <Link
                  to="/sign-in"
                  className="text-[13px] text-text-muted transition-colors hover:text-text"
                >
                  Sign in
                </Link>
              </li>
              <li>
                <Link
                  to="/sign-up"
                  className="text-[13px] text-text-muted transition-colors hover:text-text"
                >
                  Get started
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <div className="border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 md:px-6">
          <span className="font-mono text-[11px] text-text-faint">
            © 2026 Helix Intelligence
          </span>
          <span className="label-mono text-text-faint">all systems nominal</span>
        </div>
      </div>
    </footer>
  )
}
