import { Link } from "react-router-dom"
import { useLanguage } from "@/context/LanguageContext"
import { useW8Copy } from "@/i18n/w8Product"
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from "@/lib/supportEmail"

/** @param {{ to: string, children: import("react").ReactNode }} props */
function FooterLink({ to, children }) {
  const cls = "text-text-muted transition-colors hover:text-white"
  // Anchors, files, and mailto leave the router. App routes stay in it.
  const external = /^(?:https?:|mailto:|tel:)/.test(to) || to.includes("#") || to.endsWith(".md")
  return external ? (
    <a href={to} className={cls}>{children}</a>
  ) : (
    <Link to={to} className={cls}>{children}</Link>
  )
}

/** @param {{ title: string, links: [string, string][], className: string }} props */
function Column({ title, links, className }) {
  return (
    <div className={`flex flex-col gap-3.5 ${className}`}>
      <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text-faint">{title}</span>
      <ul className="flex flex-col gap-2.5 text-[13px]">
        {links.map(([label, to]) => (
          <li key={to}>
            <FooterLink to={to}>{label}</FooterLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Marketing footer, restored to the layout of the live landing page (grid
 * strip, HELIX watermark, product/company/legal columns, status bar). Links
 * point only at pages that exist; legal pages are the draft disclosures.
 */
export function MarketingFooter() {
  const { t } = useLanguage()
  const c = useW8Copy()

  return (
    <footer className="relative overflow-hidden border-t border-white/[0.08] bg-[#050508] font-sans text-text-muted">
      <div className="absolute inset-x-0 top-0 z-10 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" aria-hidden="true" />

      <div className="relative h-12 w-full overflow-hidden border-b border-white/[0.06] sm:h-14" aria-hidden="true">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)",
            backgroundSize: "36px 36px",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#050508]/90" />
      </div>

      <div className="relative px-6 py-14 sm:px-8 sm:py-20 lg:px-12">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0 flex select-none items-center justify-center overflow-hidden" dir="ltr">
          <span className="whitespace-nowrap font-sans text-[clamp(7rem,25vw,22rem)] font-black uppercase leading-none tracking-[-0.04em] text-white/[0.11]">
            HELIX
          </span>
        </div>

        <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-12 sm:grid-cols-2 md:grid-cols-12 lg:gap-16">
          <div className="flex flex-col gap-4 sm:col-span-2 md:col-span-5 lg:col-span-4">
            <Link to="/" className="text-2xl font-bold tracking-tight text-white">
              Helix Intelligence
            </Link>
            <p className="max-w-sm text-[13.5px] leading-relaxed text-text-muted">{c.footerTagline}</p>
          </div>

          <Column
            title={c.footerProduct}
            className="sm:col-span-1 md:col-span-2 lg:col-span-3"
            links={[
              [t("marketingDiscoverTitle"), "/discover"],
              [t("marketingCreativeTitle"), "/monitors"],
              [t("marketingWorkspaceTitle"), "/swipe-files"],
              [c.footerChangelog, "/updates"],
            ]}
          />
          <Column
            title={c.footerCompany}
            className="sm:col-span-1 md:col-span-2 lg:col-span-2"
            links={[
              [c.footerAbout, "/#product"],
              [t("docsNavigation"), "/docs"],
              [c.footerApiReference, "/docs/api-reference/authentication"],
              [c.footerRequestAccess, "/#access"],
              [c.footerSupport, SUPPORT_MAILTO],
              [c.footerAgents, "/agents.md"],
            ]}
          />
          <Column
            title={c.footerLegalTitle}
            className="sm:col-span-1 md:col-span-3 lg:col-span-3"
            links={[
              [c.footerTerms, "/terms"],
              [c.footerPrivacy, "/privacy"],
              [c.footerSubprocessors, "/legal/subprocessors"],
              [c.footerCookies, "/cookies"],
            ]}
          />
        </div>
      </div>

      <div className="border-t border-white/[0.06] bg-[#040407] px-6 py-4 text-center font-mono text-[11px] text-text-faint sm:px-8 lg:px-12">
        <p className="mx-auto max-w-4xl leading-relaxed">
          {t("footerDisclosure")} {t("footerDraft")}{" "}
          <a href={SUPPORT_MAILTO} className="text-text-muted underline decoration-white/20 underline-offset-2 transition-colors hover:text-white">{SUPPORT_EMAIL}</a>
        </p>
      </div>

      <div className="border-t border-white/[0.08] bg-[#050608]/90">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-4 px-6 py-5 sm:flex-row sm:px-8 lg:px-12">
          <div className="font-mono text-xs uppercase tracking-wider text-text-faint">{c.footerCopyright}</div>
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-faint">
            <span className="h-2 w-2 rounded-[1px] bg-accent/80 shadow-[0_0_8px_rgba(215,255,79,0.5)]" aria-hidden="true" />
            <span>{c.footerStatus}</span>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default MarketingFooter
