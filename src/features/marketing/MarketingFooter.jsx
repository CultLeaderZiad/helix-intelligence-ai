import { Link } from "react-router-dom"
import { Logo } from "@/components/ui/Logo"

function GithubIcon({ className = "h-3.5 w-3.5", ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} {...props}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  )
}

/**
 * Public footer. Same hairline/mono system as the rest of the site; the
 * columns re-list the section anchors and the two auth entry points so the
 * whole public surface is reachable from the bottom of the page too.
 */
const COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "Overview", href: "#product" },
      { label: "Pricing", href: "#pricing" },
      { label: "Docs", href: "#docs" },
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
                    <a
                      href={link.href}
                      className="text-[13px] text-text-muted transition-colors hover:text-text"
                    >
                      {link.label}
                    </a>
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
          <div className="flex items-center gap-3">
            <img
              src="/brand/helix-logo.png"
              alt="Helix"
              className="h-4 w-4 rounded-[2px] object-contain opacity-80"
            />
            <span className="font-mono text-[11px] text-text-faint">
              Powered by Helix · © 2026 Helix Intelligence
            </span>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com/CultLeaderZiad/helix-intelligence-ai"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Helix on GitHub"
              className="flex items-center gap-1.5 font-mono text-[11px] text-text-muted hover:text-text transition-colors"
            >
              <Github className="h-3.5 w-3.5" />
              <span>GitHub</span>
            </a>
            <span className="text-border-strong hidden sm:inline">·</span>
            <span className="label-mono text-text-faint hidden sm:inline">all systems nominal</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
