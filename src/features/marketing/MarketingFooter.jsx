import React, { useState } from "react"
import { Link } from "react-router-dom"
import { X, Shield, FileText, Lock, Cookie } from "lucide-react"

const LEGAL_DOCS = {
  terms: {
    title: "Terms of Service",
    icon: FileText,
    updated: "September 2026",
    content: [
      {
        heading: "1. Platform Usage & License",
        body: "Helix Intelligence grants authorized users a non-exclusive, non-transferable right to access the workstation, competitor intelligence queries, and creative remix studio in accordance with their subscription tier.",
      },
      {
        heading: "2. Data Extraction & Scraper Ethics",
        body: "Our distributed crawler infrastructure operates exclusively against public ad libraries and verified social channels in strict adherence to robots.txt and automated rate limits.",
      },
      {
        heading: "3. Creative IP & Commercial Rights",
        body: "Any creative assets generated or remixed within the Create Studio remain 100% the intellectual property of the account holder. Helix does not claim royalties or proprietary rights over user-generated marketing collateral.",
      },
      {
        heading: "4. Service Level & Termination",
        body: "We maintain a 99.9% uptime target. Accounts violating fair API consumption or reverse-engineering policies may be terminated upon written notice.",
      },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    icon: Lock,
    updated: "September 2026",
    content: [
      {
        heading: "1. Information We Collect",
        body: "We collect account profile information (email, team name), authentication credentials, and search history necessary to provide the intelligence workspace. We never access private customer advertising accounts or unreleased assets.",
      },
      {
        heading: "2. Zero Third-Party Monetization",
        body: "Helix Intelligence never sells, rents, or exchanges user telemetry or competitor search dossiers with third-party ad brokers.",
      },
      {
        heading: "3. Global Compliance (GDPR & CCPA)",
        body: "All data storage is encrypted at rest using AES-256. Users retain the right to request a complete audit log export or account purge at any time.",
      },
    ],
  },
  security: {
    title: "Security & Infrastructure",
    icon: Shield,
    updated: "September 2026",
    content: [
      {
        heading: "1. SOC2 & TLS 1.3 Standards",
        body: "All traffic across API endpoints, dashboard sessions, and edge scraping nodes is enforced with TLS 1.3 encryption and strict HTTP response headers.",
      },
      {
        heading: "2. Sandboxed AI Generation",
        body: "Generative model pipelines execute in isolated memory sandboxes. Prompt formulas and seed references are never retained in permanent training corpora.",
      },
      {
        heading: "3. Continuous Vulnerability Audits",
        body: "Automated penetration testing and daily dependency vulnerability sweeps guarantee platform integrity for enterprise brand portfolios.",
      },
    ],
  },
  cookie: {
    title: "Cookie Policy",
    icon: Cookie,
    updated: "September 2026",
    content: [
      {
        heading: "1. Essential Session Cookies",
        body: "Helix employs strictly essential HTTP-only cookies to preserve authentication sessions and tenant security tokens.",
      },
      {
        heading: "2. Zero Tracking Pixels",
        body: "We do not embed third-party behavioral advertising pixels or cross-site tracking beacons on our public or console surfaces.",
      },
    ],
  },
}

export function MarketingFooter() {
  const [activeLegalModal, setActiveLegalModal] = useState(null)

  const activeDoc = activeLegalModal ? LEGAL_DOCS[activeLegalModal] : null

  return (
    <footer className="relative bg-[#050508] border-t border-white/[0.08] overflow-hidden text-neutral-400 font-sans">
      {/* Top subtle grid lines aesthetic */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent z-10" />
      <div className="absolute top-0 inset-x-0 h-6 pointer-events-none opacity-20 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-white/10 via-transparent to-transparent z-10" />

      {/* Top Grid Border Texture strip */}
      <div className="relative h-12 sm:h-14 w-full border-b border-white/[0.06] overflow-hidden">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)`,
            backgroundSize: "36px 36px",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#050508]/90" />
      </div>

      {/* Main Footer Body with Background HELIX Watermark */}
      <div className="relative px-6 py-14 sm:px-8 sm:py-20 lg:px-12">
        {/* Massive Background Watermark Typography: "HELIX" */}
        <div 
          aria-hidden="true"
          className="absolute inset-0 flex items-center justify-center pointer-events-none select-none z-0 overflow-hidden"
        >
          <span
            className="font-sans font-black text-[clamp(7rem,25vw,22rem)] tracking-[-0.04em] text-white/[0.11] leading-none uppercase select-none pointer-events-none whitespace-nowrap"
            style={{ willChange: "transform" }}
          >
            HELIX
          </span>
        </div>

        {/* Foreground Content Columns */}
        <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-12 sm:grid-cols-2 md:grid-cols-12 lg:gap-16">
          {/* Brand Column */}
          <div className="flex flex-col gap-4 sm:col-span-2 md:col-span-5 lg:col-span-4">
            <Link to="/" className="flex items-center gap-2.5 text-white">
              <span className="text-2xl font-bold tracking-tight text-white font-sans">
                Helix Intelligence
              </span>
            </Link>
            <p className="max-w-sm text-[13.5px] leading-relaxed text-text-muted">
              The creative discovery, intelligence, and ad performance
              workstation — built for serious growth teams.
            </p>
          </div>

          {/* Product Column */}
          <div className="flex flex-col gap-3.5 sm:col-span-1 md:col-span-2 lg:col-span-3">
            <span className="font-mono text-[11px] font-semibold tracking-wider text-text-faint uppercase">
              PRODUCT
            </span>
            <ul className="flex flex-col gap-2.5 text-[13px]">
              <li>
                <Link to="/discover" className="text-text-muted hover:text-white transition-colors">
                  Discover
                </Link>
              </li>
              <li>
                <Link to="/intelligence" className="text-text-muted hover:text-white transition-colors">
                  Intelligence
                </Link>
              </li>
              <li>
                <Link to="/create" className="text-text-muted hover:text-white transition-colors">
                  Create Studio
                </Link>
              </li>
              <li>
                <Link to="/monitors" className="text-text-muted hover:text-white transition-colors">
                  Monitors
                </Link>
              </li>
              <li>
                <Link to="/performance" className="text-text-muted hover:text-white transition-colors">
                  Performance
                </Link>
              </li>
              <li>
                <Link to="/updates" className="text-text-muted hover:text-white transition-colors">
                  Changelog & Updates
                </Link>
              </li>
            </ul>
          </div>

          {/* Company Column */}
          <div className="flex flex-col gap-3.5 sm:col-span-1 md:col-span-2 lg:col-span-2">
            <span className="font-mono text-[11px] font-semibold tracking-wider text-text-faint uppercase">
              COMPANY
            </span>
            <ul className="flex flex-col gap-2.5 text-[13px]">
              <li>
                <a href="/#product" className="text-text-muted hover:text-white transition-colors">
                  About
                </a>
              </li>
              <li>
                <Link to="/docs" className="text-text-muted hover:text-white transition-colors">
                  Documentation
                </Link>
              </li>
              <li>
                <Link to="/docs/api-reference/authentication" className="text-text-muted hover:text-white transition-colors">
                  API Reference
                </Link>
              </li>
              <li>
                <a href="/#pricing" className="text-text-muted hover:text-white transition-colors">
                  Pricing
                </a>
              </li>
              <li>
                <Link to="/updates" className="text-text-muted hover:text-white transition-colors">
                  Press & Releases
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal Column */}
          <div className="flex flex-col gap-3.5 sm:col-span-1 md:col-span-3 lg:col-span-3">
            <span className="font-mono text-[11px] font-semibold tracking-wider text-text-faint uppercase">
              LEGAL
            </span>
            <ul className="flex flex-col gap-2.5 text-[13px]">
              <li>
                <button
                  type="button"
                  onClick={() => setActiveLegalModal("terms")}
                  className="cursor-pointer text-left text-text-muted hover:text-white transition-colors"
                >
                  Terms of Service
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => setActiveLegalModal("privacy")}
                  className="cursor-pointer text-left text-text-muted hover:text-white transition-colors"
                >
                  Privacy Policy
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => setActiveLegalModal("security")}
                  className="cursor-pointer text-left text-text-muted hover:text-white transition-colors"
                >
                  Security
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => setActiveLegalModal("cookie")}
                  className="cursor-pointer text-left text-text-muted hover:text-white transition-colors"
                >
                  Cookie Policy
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom Hairline & Operational Status Bar — matching screenshot */}
      <div className="border-t border-white/[0.08] bg-[#050608]/90">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-4 px-6 py-5 sm:flex-row sm:px-8 lg:px-12">
          {/* Left copyright notice */}
          <div className="font-mono text-xs uppercase tracking-wider text-text-faint">
            © 2026 HELIX. ALL RIGHTS RESERVED.
          </div>

          {/* Right systems indicator */}
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-faint">
            <span className="h-2 w-2 rounded-[1px] bg-[#ccff00] shadow-[0_0_8px_#ccff0088]" />
            <span>ALL SYSTEMS OPERATIONAL</span>
          </div>
        </div>
      </div>

      {/* Legal Dialog Modal */}
      {activeLegalModal && activeDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="relative w-full max-w-2xl rounded-xl border border-border bg-surface p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2.5">
                <activeDoc.icon className="h-5 w-5 text-accent" />
                <h3 className="text-lg font-bold text-text">{activeDoc.title}</h3>
                <span className="font-mono text-[10px] text-text-faint px-2 py-0.5 rounded bg-surface-2 border border-border">
                  Updated {activeDoc.updated}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setActiveLegalModal(null)}
                className="cursor-pointer rounded p-1.5 text-text-muted hover:bg-surface-2 hover:text-text transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="max-h-[60vh] space-y-5 overflow-y-auto pr-2 text-sm text-text-muted leading-relaxed">
              {activeDoc.content.map((sec) => (
                <div key={sec.heading} className="space-y-1.5">
                  <h4 className="font-semibold text-text text-sm">{sec.heading}</h4>
                  <p className="text-xs text-text-muted">{sec.body}</p>
                </div>
              ))}
            </div>

            <div className="flex justify-end border-t border-border pt-4">
              <button
                type="button"
                onClick={() => setActiveLegalModal(null)}
                className="cursor-pointer px-4 py-2 rounded border border-border bg-surface-2 text-xs font-mono uppercase tracking-wider text-text hover:bg-surface-3 transition-colors"
              >
                Close Disclosure
              </button>
            </div>
          </div>
        </div>
      )}
    </footer>
  )
}

export default MarketingFooter
