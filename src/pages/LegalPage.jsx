import React, { useState, useEffect } from "react"
import { useLocation, Link } from "react-router-dom"
import { Shield, FileText, Lock, Cookie, ArrowLeft, ExternalLink, Mail, CheckCircle2, AlertTriangle } from "lucide-react"
import { PillNav } from "@/components/ui/PillNav"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"

const SECTIONS = [
  { id: "privacy", label: "Privacy Policy", icon: Lock, path: "/privacy" },
  { id: "terms", label: "Terms of Service", icon: FileText, path: "/terms" },
  { id: "cookies", label: "Cookie Policy", icon: Cookie, path: "/cookies" },
  { id: "subprocessors", label: "Sub-processors", icon: Shield, path: "/legal/subprocessors" },
]

export function LegalPage() {
  const location = useLocation()
  
  // Determine active tab from URL path
  const getTabFromPath = (pathname) => {
    if (pathname.includes("terms")) return "terms"
    if (pathname.includes("cookie")) return "cookies"
    if (pathname.includes("subprocessor")) return "subprocessors"
    return "privacy"
  }

  const [activeTab, setActiveTab] = useState(getTabFromPath(location.pathname))

  useEffect(() => {
    setActiveTab(getTabFromPath(location.pathname))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-[#07070a] text-text font-sans antialiased selection:bg-accent selection:text-black">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 border-b border-border bg-[#07070a]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2.5 text-text hover:text-white transition-colors">
            <ArrowLeft className="h-4 w-4 text-accent" aria-hidden="true" />
            <span className="font-mono text-xs uppercase tracking-wider text-text-muted hover:text-text">Back to Home</span>
          </Link>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-[1px] bg-accent animate-pulse" aria-hidden="true" />
            <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted">Pre-revenue Beta Compliance</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        {/* Page Title & Intro */}
        <div className="space-y-4 border-b border-border pb-8">
          <div className="inline-flex items-center gap-2 rounded border border-accent/20 bg-accent/5 px-2.5 py-1 font-mono text-[11px] text-accent">
            <Shield className="h-3.5 w-3.5" aria-hidden="true" />
            <span>OPERATIONAL TRANSPARENCY & DATA HONESTY</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-text">
            Helix Intelligence Legal Documents
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-text-muted">
            Plain-English policies governing our competitive intelligence workstation, privacy practices, data processing, and platform usage terms.
          </p>

          {/* Legal Draft Notice */}
          <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-amber-200/90 leading-relaxed">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <strong className="font-semibold text-amber-300">Beta Regulatory Notice: </strong>
                Helix is operated by Ziad Sabry in Cairo, Egypt. These documents reflect our current pre-revenue beta implementation under GDPR, CPRA, and Egypt PDPL (Law 151/2020) baselines. Formal corporate entity formation and final legal counsel review will precede commercial payment processing.
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav aria-label="Legal document tabs" className="mt-8 flex flex-wrap gap-2 border-b border-border pb-4">
          {SECTIONS.map((sec) => {
            const Icon = sec.icon
            const isActive = activeTab === sec.id
            return (
              <Link
                key={sec.id}
                to={sec.path}
                onClick={() => setActiveTab(sec.id)}
                className={`inline-flex items-center gap-2 rounded px-3.5 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${
                  isActive
                    ? "bg-accent text-black font-semibold shadow-sm"
                    : "bg-surface-2 text-text-muted hover:bg-surface-3 hover:text-text"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-black" : "text-text-faint"}`} aria-hidden="true" />
                {sec.label}
              </Link>
            )
          })}
        </nav>

        {/* Content Body */}
        <article className="mt-8 space-y-10 rounded-xl border border-border bg-surface p-6 sm:p-10 shadow-xl leading-relaxed">
          {/* TAB 1: PRIVACY POLICY */}
          {activeTab === "privacy" && (
            <div className="space-y-8">
              <div className="border-b border-border pb-4">
                <span className="font-mono text-[11px] text-text-faint uppercase">Document Reference: PP-2026-BETA</span>
                <h2 className="text-2xl font-bold text-text mt-1">Privacy Policy</h2>
                <p className="font-mono text-xs text-text-muted mt-1">Last updated: October 2026</p>
              </div>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">1. Who We Are</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Helix (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;) is an advertising intelligence and creative analysis platform operated by <strong>Helix, operated by Ziad Sabry</strong>, located in Cairo, Egypt. This Privacy Policy explains what personal data we collect, why we process it, and your legal rights regarding your personal information.
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">2. What We Collect</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  We collect strictly the minimum personal data required to provide our service:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li><strong>Account Data:</strong> Name, work email address, and cryptographically hashed passwords.</li>
                  <li><strong>Usage Data:</strong> Ad discovery search queries, saved creative swipe files, workspace credit allocations, feature usage metrics, and IP address/browser user agent for security and abuse prevention.</li>
                  <li><strong>Content You Provide:</strong> Creative briefs, uploaded reference media, and support ticket correspondence.</li>
                  <li><strong>Generated Content:</strong> AI-generated pattern analyses, audience simulations, and creative briefs created through the service, associated with your workspace account.</li>
                  <li><strong>Payment Information:</strong> <em>Not applicable during pre-revenue beta</em>. Commercial payment processing (e.g., Stripe) will be handled directly by certified third-party payment gateways; Helix does not store raw credit card numbers.</li>
                </ul>
                <div className="p-3 bg-surface-2 rounded border border-border font-mono text-xs text-text-muted">
                  <strong>Data Minimization Commitment:</strong> We do not collect unnecessary profile fields (such as phone numbers, personal physical addresses, or birthdays) and we <strong>never sell or rent personal data</strong>.
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">3. Why We Process Your Data (Legal Basis)</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  We process data under legitimate interest and contractual necessity:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li>To authenticate you and operate the competitive intelligence workstation.</li>
                  <li>To enforce query quotas, credit limits, and rate-limiting protections.</li>
                  <li>To communicate transactional service notifications, support ticket responses, and (with optional consent) product release updates.</li>
                  <li>To maintain platform reliability and protect against automated denial-of-service or scraping attacks.</li>
                </ul>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">4. Third-Party Sub-processors</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  We share data only with verified technical infrastructure providers bound by strict confidentiality and data protection agreements:
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border">
                    <thead className="bg-surface-2 font-mono text-[11px] text-text-faint uppercase border-b border-border">
                      <tr>
                        <th className="p-2.5">Provider</th>
                        <th className="p-2.5">Purpose</th>
                        <th className="p-2.5">Region</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-text-muted">
                      <tr><td className="p-2.5 font-medium text-text">Neon Inc.</td><td className="p-2.5">Managed Serverless PostgreSQL Database</td><td className="p-2.5">US / EU</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Render Services Inc.</td><td className="p-2.5">Backend FastAPI application hosting</td><td className="p-2.5">US East</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Vercel Inc.</td><td className="p-2.5">Frontend SPA hosting & Edge Delivery</td><td className="p-2.5">Global Edge</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Cloudflare Inc.</td><td className="p-2.5">R2 generated media storage & CDN</td><td className="p-2.5">Global</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Groq, OpenRouter, Google Gemini</td><td className="p-2.5">AI analysis and creative synthesis models</td><td className="p-2.5">US / Global</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Metapi, Adyntel, ScrapeGraphAI</td><td className="p-2.5">Public ad library indexing & landing-page metadata</td><td className="p-2.5">US / Global</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Higgsfield AI</td><td className="p-2.5">Premium generative video/motion synthesis</td><td className="p-2.5">US</td></tr>
                      <tr><td className="p-2.5 font-medium text-text">Resend Inc.</td><td className="p-2.5">Transactional transactional system emails</td><td className="p-2.5">US</td></tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">5. International Data Transfers</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Because our hosting and AI infrastructure partners operate globally, personal data may be stored or processed in the United States and European Union. We ensure our vendors adhere to Standard Contractual Clauses (SCCs) and robust technical safeguards compliant with GDPR, UK GDPR, and Egyptian Law 151/2020.
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">6. Your Data Protection Rights</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Regardless of your location, you have the following rights:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li><strong>Right to Access:</strong> Request a copy of all personal data held about you.</li>
                  <li><strong>Right to Rectification:</strong> Correct any incomplete or inaccurate profile information via Settings.</li>
                  <li><strong>Right to Erasure (Right to be Forgotten):</strong> Request permanent deletion of your account and associated records within 30 days.</li>
                  <li><strong>Right to Data Portability:</strong> Receive your saved swipe files, briefs, and query logs in a structured JSON export.</li>
                  <li><strong>Right to Withdraw Consent:</strong> Opt out of optional marketing or promotional communications at any time.</li>
                </ul>
                <p className="text-xs sm:text-sm text-text-muted">
                  To exercise any of these rights, contact us at <a href="mailto:cultleaderzoz.dev@gmail.com" className="text-accent underline">cultleaderzoz.dev@gmail.com</a>.
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">7. Data Retention & Deletion</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  We retain account credentials and workspace records for as long as your workspace remains active. Upon verified account closure or deletion request, your personal data is purged from our production databases within 30 days, except where temporary audit logs must be maintained for legal compliance.
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">8. Children&rsquo;s Privacy</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Helix Intelligence is a B2B marketing research tool intended for professionals. We do not knowingly collect or solicit data from children under the age of 16.
                </p>
              </section>

              <section className="space-y-3 border-t border-border pt-4">
                <h3 className="text-base font-semibold text-text">9. Contact</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Operator: Helix, operated by Ziad Sabry · Cairo, Egypt<br />
                  Direct Privacy Contact: <a href="mailto:cultleaderzoz.dev@gmail.com" className="text-accent underline">cultleaderzoz.dev@gmail.com</a> / <a href="mailto:support@helix-intelligence.com" className="text-accent underline">support@helix-intelligence.com</a>
                </p>
              </section>
            </div>
          )}

          {/* TAB 2: TERMS OF SERVICE */}
          {activeTab === "terms" && (
            <div className="space-y-8">
              <div className="border-b border-border pb-4">
                <span className="font-mono text-[11px] text-text-faint uppercase">Document Reference: TOS-2026-BETA</span>
                <h2 className="text-2xl font-bold text-text mt-1">Terms of Service</h2>
                <p className="font-mono text-xs text-text-muted mt-1">Last updated: October 2026</p>
              </div>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">1. Acceptance of Terms</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  By accessing Helix Intelligence, registering an account, or connecting to our APIs, you enter into a binding agreement with Helix (&ldquo;Helix,&rdquo; &ldquo;we,&rdquo; &ldquo;us&rdquo;), operated by Ziad Sabry. If you do not agree, you must discontinue use immediately.
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">2. Nature of the Service & Data Disclaimers</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Helix provides competitive marketing intelligence, public ad library search, pattern analysis, and AI-assisted creative synthesis tools. You acknowledge and accept the following inherent limitations:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li><strong>Third-Party Ad Archive Coverage:</strong> Competitor ad data is indexed from public third-party archives (such as the Meta Ad Library). Coverage may be subject to geographic, platform, or temporal provider skews (e.g. Meta&rsquo;s commercial disclosure rules favoring EU/UK commercial records). Helix does not warrant that ad records are exhaustive or real-time.</li>
                  <li><strong>AI Insights & Estimates:</strong> All generative teardowns, fatigue alerts, and audience simulation projections are synthetic interpretations and statistical estimations, not guarantees of real-world ad performance. Audience simulation is a creative rehearsal aid, not a predictor of market outcomes.</li>
                  <li><strong>Explicit Data Labeling:</strong> Helix clearly distinguishes reported public archive metadata from synthetic modeled metrics. You agree to evaluate simulated metrics with appropriate professional discretion.</li>
                </ul>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">3. Accounts & Preview Terms</h3>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li>You must maintain the confidentiality of your workspace login credentials and API tokens.</li>
                  <li>During this pre-revenue beta preview, trial allocations and access credits are provided free of charge or per preview agreement. We reserve the right to modify trial parameters or limit abuse.</li>
                  <li>Accounts engaging in denial-of-service, automated bulk scraping of our interface, or security vulnerability exploitation may be suspended immediately.</li>
                </ul>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">4. Acceptable Use Policy</h3>
                <p className="text-xs sm:text-sm text-text-muted">You agree not to:</p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-text-muted">
                  <li>Use the service to generate deceptive, defamatory, or unlawful advertising collateral.</li>
                  <li>Attempt to bypass API quota rate limits or credit billing meters.</li>
                  <li>Misrepresent competitor advertisements or produce fraudulent impersonation creatives.</li>
                  <li>Attempt to reverse-engineer, decompile, or extract the proprietary heuristics of the Helix platform or underlying models.</li>
                  <li>Resell, redistribute, or syndicate raw intelligence data feeds without an explicit enterprise agreement.</li>
                </ul>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">5. Intellectual Property Rights</h3>
                <div className="space-y-3 text-xs sm:text-sm text-text-muted">
                  <p>
                    <strong>Your Content & Generations:</strong> You retain ownership of all creative briefs, uploaded reference visual assets, and generative creative outputs generated through the Create Studio associated with your workspace account, subject to third-party rights in source references.
                  </p>
                  <p>
                    <strong>Helix Intellectual Property:</strong> Helix and its licensors retain exclusive ownership of the platform software, algorithms, user interface designs, pattern-detection taxonomies, and aggregated analytical benchmarks.
                  </p>
                  <p>
                    <strong>Third-Party Competitor Ad Content:</strong> All competitor ad assets, videos, logos, and trademarks indexed from public advertising archives remain the intellectual property of their respective brand owners. Helix displays such materials strictly for transformative comparative analysis and market research under fair use principles, with explicit brand and source platform attribution.
                  </p>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">6. Warranty Disclaimer & Limitation of Liability</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  HELIX IS PROVIDED ON AN &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; BASIS WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE MAXIMUM EXTENT PERMITTED BY LAW, HELIX AND OPERATOR ZIAD SABRY SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES (INCLUDING LOSS OF ADVERTISING BUDGET OR REVENUE). OUR MAXIMUM AGGREGATE LIABILITY FOR ALL CLAIMS ARISING OUT OF YOUR USE OF THE SERVICE IS LIMITED TO THE AMOUNT PAID BY YOU TO HELIX IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM (OR $100 USD DURING FREE PREVIEW STATUS).
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">7. Governing Law</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  These Terms are governed by and construed in accordance with the laws of the Arab Republic of Egypt, without regard to conflict-of-law principles.
                </p>
              </section>

              <section className="space-y-3 border-t border-border pt-4">
                <h3 className="text-base font-semibold text-text">8. Contact Information</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Legal queries and terms inquiries: <a href="mailto:cultleaderzoz.dev@gmail.com" className="text-accent underline">cultleaderzoz.dev@gmail.com</a>
                </p>
              </section>
            </div>
          )}

          {/* TAB 3: COOKIE & STORAGE POLICY */}
          {activeTab === "cookies" && (
            <div className="space-y-8">
              <div className="border-b border-border pb-4">
                <span className="font-mono text-[11px] text-text-faint uppercase">Document Reference: CK-2026-BETA</span>
                <h2 className="text-2xl font-bold text-text mt-1">Cookie & Local Storage Policy</h2>
                <p className="font-mono text-xs text-text-muted mt-1">Last updated: October 2026 (Verified via Technical Embed Audit)</p>
              </div>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">1. Zero Third-Party Advertising Cookies</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Helix Intelligence respects digital privacy. <strong>We do not deploy marketing cookies, behavioral retargeting pixels (such as Meta Pixel or Google Ads tags), or cross-site tracking beacons.</strong>
                </p>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">2. Complete Storage Inventory</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Our application uses modern browser <code className="text-accent">localStorage</code> strictly for necessary session authentication and user interface preferences:
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border">
                    <thead className="bg-surface-2 font-mono text-[11px] text-text-faint uppercase border-b border-border">
                      <tr>
                        <th className="p-2.5">Key / Item</th>
                        <th className="p-2.5">Category</th>
                        <th className="p-2.5">Storage Type</th>
                        <th className="p-2.5">Purpose &amp; Expiration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-text-muted">
                      <tr>
                        <td className="p-2.5 font-mono text-text">helix_access_token</td>
                        <td className="p-2.5"><span className="text-accent font-semibold">Strictly Essential</span></td>
                        <td className="p-2.5">localStorage</td>
                        <td className="p-2.5">Stores the active API session bearer token to authenticate requests against our FastAPI backend. Cleared on sign out.</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-mono text-text">helix_cached_user</td>
                        <td className="p-2.5"><span className="text-accent font-semibold">Strictly Essential</span></td>
                        <td className="p-2.5">localStorage</td>
                        <td className="p-2.5">Caches user identity, role (admin/member), and workspace plan to avoid screen flicker during page transitions.</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-mono text-text">theme</td>
                        <td className="p-2.5">Functional</td>
                        <td className="p-2.5">localStorage</td>
                        <td className="p-2.5">Preserves your preferred visual mode (Dark / High-Contrast mode).</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">3. Why You Do Not See a Cookie Tracking Banner</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Under the European Union ePrivacy Directive (Directive 2002/58/EC), GDPR Article 6, and Egyptian Law 151/2020, technologies stored exclusively for the technical transmission of communications or strictly necessary to facilitate a service explicitly requested by the user (such as user session authentication) are exempt from cookie consent banners.
                </p>
                <div className="p-3 bg-surface-2 rounded border border-border text-xs text-text-muted">
                  If non-essential third-party analytics or marketing pixels are introduced in future versions, a compliant consent management modal will be implemented prior to activation.
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-text">4. Managing Browser Storage</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  You can clear your local storage at any time through your browser settings (&ldquo;Clear Browsing Data&rdquo; &rarr; &ldquo;Cookies and Site Data&rdquo;). Note that clearing local storage will log you out of your current Helix workstation session.
                </p>
              </section>

              <section className="space-y-3 border-t border-border pt-4">
                <h3 className="text-base font-semibold text-text">5. Contact</h3>
                <p className="text-xs sm:text-sm text-text-muted">
                  Inquiries regarding data storage: <a href="mailto:cultleaderzoz.dev@gmail.com" className="text-accent underline">cultleaderzoz.dev@gmail.com</a>
                </p>
              </section>
            </div>
          )}

          {/* TAB 4: SUB-PROCESSORS */}
          {activeTab === "subprocessors" && (
            <div className="space-y-8">
              <div className="border-b border-border pb-4">
                <span className="font-mono text-[11px] text-text-faint uppercase">Document Reference: SP-2026-BETA</span>
                <h2 className="text-2xl font-bold text-text mt-1">Authorized Sub-processors</h2>
                <p className="font-mono text-xs text-text-muted mt-1">Last updated: October 2026</p>
              </div>

              <p className="text-xs sm:text-sm text-text-muted">
                To deliver our real-time ad search, AI analysis, and creative synthesis services, Helix partners with industry-leading cloud and model providers. Every sub-processor is evaluated for robust technical encryption standards, uptime SLA reliability, and data privacy safeguards.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-border">
                  <thead className="bg-surface-2 font-mono text-[11px] text-text-faint uppercase border-b border-border">
                    <tr>
                      <th className="p-2.5">Sub-processor</th>
                      <th className="p-2.5">Service Purpose</th>
                      <th className="p-2.5">Processing Location</th>
                      <th className="p-2.5">Safeguards</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-text-muted">
                    <tr>
                      <td className="p-2.5 font-medium text-text">Neon Inc.</td>
                      <td className="p-2.5">Serverless PostgreSQL persistence, user records, and encrypted tokens</td>
                      <td className="p-2.5">US / EU</td>
                      <td className="p-2.5">SOC 2 Type II, TLS 1.3, AES-256 at rest</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Render Services Inc.</td>
                      <td className="p-2.5">Backend FastAPI services, worker queues, and orchestration</td>
                      <td className="p-2.5">US East</td>
                      <td className="p-2.5">SOC 2 Type II, isolated VPC containers</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Vercel Inc.</td>
                      <td className="p-2.5">Frontend Single Page Application delivery and edge caching</td>
                      <td className="p-2.5">Global Edge</td>
                      <td className="p-2.5">SOC 2 Type II, ISO 27001</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Cloudflare Inc.</td>
                      <td className="p-2.5">R2 zero-egress object storage for generated creatives</td>
                      <td className="p-2.5">Global</td>
                      <td className="p-2.5">SOC 2 Type II, Encrypted object storage</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Groq Inc.</td>
                      <td className="p-2.5">Ultra low-latency LPU model inference for creative scoring</td>
                      <td className="p-2.5">US</td>
                      <td className="p-2.5">Zero data retention agreement, TLS in transit</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">OpenRouter / Google Gemini</td>
                      <td className="p-2.5">Multimodal LLM analysis and audience simulation pipelines</td>
                      <td className="p-2.5">US / Global</td>
                      <td className="p-2.5">Enterprise API no-train agreements</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Metapi &amp; Adyntel</td>
                      <td className="p-2.5">Public ad library indexing and query coordination</td>
                      <td className="p-2.5">US / Global</td>
                      <td className="p-2.5">Public commercial ad archives only</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">ScrapeGraphAI</td>
                      <td className="p-2.5">Automated competitor landing-page structure extraction</td>
                      <td className="p-2.5">US / Global</td>
                      <td className="p-2.5">Public web scraping compliant with robots.txt</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Higgsfield AI</td>
                      <td className="p-2.5">High-fidelity generative motion and video creative rendering</td>
                      <td className="p-2.5">US</td>
                      <td className="p-2.5">Secure transient compute sandboxes</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium text-text">Resend Inc.</td>
                      <td className="p-2.5">Transactional system notifications and password reset emails</td>
                      <td className="p-2.5">US</td>
                      <td className="p-2.5">SOC 2, DKIM/SPF/DMARC authenticated</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="space-y-2 border-t border-border pt-4 text-xs text-text-muted">
                <p>
                  <strong>Sub-processor Modifications:</strong> When we onboard new technical infrastructure providers, this register is updated prior to production routing. Workspace administrators may subscribe to compliance notifications by contacting <a href="mailto:cultleaderzoz.dev@gmail.com" className="text-accent underline">cultleaderzoz.dev@gmail.com</a>.
                </p>
              </div>
            </div>
          )}
        </article>

        {/* Footer Support Prompt */}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-lg border border-border bg-surface-2 p-5 text-xs">
          <div className="flex items-center gap-3">
            <Mail className="h-4 w-4 text-accent shrink-0" aria-hidden="true" />
            <span className="text-text-muted">
              Have questions about our data practices or compliance standards? Reach our team directly.
            </span>
          </div>
          <a
            href="mailto:cultleaderzoz.dev@gmail.com"
            className="cursor-pointer inline-flex items-center gap-1.5 rounded bg-surface-3 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-text hover:bg-accent hover:text-black transition-colors"
          >
            Contact Privacy Officer
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        </div>
      </main>

      <MarketingFooter />
    </div>
  )
}

export default LegalPage
