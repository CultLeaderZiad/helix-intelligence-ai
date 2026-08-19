import { PublicHeader } from "@/app/PublicHeader"

/**
 * Shared frame for the pre-auth pages. Public surface (PublicHeader), not
 * the app shell.
 *
 * Deliberately NOT the "white card floating on a gradient blob" template:
 * a single max-width column sits on the app's hairline grid backdrop, and
 * the form lives in the same bordered `surface` box the app uses for its
 * terminal states — so signing in feels like operating a technical tool,
 * not landing on a marketing page. No gradient, no glass, no shadow.
 */
export function AuthLayout({ eyebrow, title, description, children, footer }) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <PublicHeader />

      <main className="grid-backdrop relative flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="flex w-full max-w-[380px] flex-col gap-6">
          <header className="flex flex-col gap-2">
            {eyebrow ? (
              <span className="font-mono text-[10px] uppercase leading-none tracking-[0.12em] text-accent-dim">
                {eyebrow}
              </span>
            ) : null}
            <h1 className="text-pretty text-lg font-medium leading-tight tracking-tight text-text">
              {title}
            </h1>
            {description ? (
              <p className="text-pretty text-[13px] leading-relaxed text-text-muted">
                {description}
              </p>
            ) : null}
          </header>

          <div className="rounded-sm border border-border bg-surface p-5">
            {children}
          </div>

          {footer ? (
            <p className="text-center text-xs leading-relaxed text-text-muted">
              {footer}
            </p>
          ) : null}
        </div>
      </main>
    </div>
  )
}
