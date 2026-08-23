import { Link } from "react-router-dom"
import { ArrowRight, Sparkles, Check, TrendingUp, Layers, Zap, Eye, Terminal as TerminalIcon } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

/**
 * =======================================================================
 * STATIC MARKETING HERO SECTION — Illustrative Public Component
 * =======================================================================
 * NOTE: The terminal readout and phone mockup below are illustrative
 * static marketing presentations designed to reflect the real instrument-
 * grade UI of Helix without executing live API or scraping calls.
 * Do not confuse with authenticated in-app components.
 * =======================================================================
 */

const PRODUCT_STEPS = [
  {
    num: "01",
    label: "DISCOVER",
    desc: "Scrape live competitor ad libraries and track high-velocity campaigns across Meta & TikTok.",
  },
  {
    num: "02",
    label: "ANALYZE",
    desc: "Extract visual hooks, copy structures, CTA triggers, and historical run lengths.",
  },
  {
    num: "03",
    label: "UNDERSTAND",
    desc: "Cluster winning creative patterns and surface fatigue signals before spending spend.",
  },
  {
    num: "04",
    label: "CREATE",
    desc: "Generate production-ready briefs and high-converting script variants from validated data.",
  },
  {
    num: "05",
    label: "OPTIMIZE",
    desc: "Continuously benchmark your own creative output against top industry performers.",
    isLast: true,
  },
]

export function Hero() {
  return (
    <section className="grid-backdrop relative border-b border-border bg-bg overflow-hidden">
      <div className="mx-auto flex w-full max-w-6xl flex-col px-4 py-16 md:px-6 md:py-24">
        
        {/* --- Top Status Badge --- */}
        <div className="flex items-center">
          <div className="inline-flex items-center gap-2 rounded-[4px] border border-border bg-surface px-3 py-1.5">
            <span
              className="h-1.5 w-1.5 rounded-full bg-accent shrink-0 animate-pulse"
              style={{ boxShadow: "0 0 6px rgba(215, 255, 79, 0.7)" }}
              aria-hidden="true"
            />
            <span className="font-mono text-[10.5px] font-medium tracking-[0.14em] uppercase text-text">
              Trial Live · 7-Day Access · Free Credits Included
            </span>
          </div>
        </div>

        {/* --- Headline & Subtitle --- */}
        <h1 className="mt-6 max-w-4xl text-balance text-3xl font-semibold leading-[1.08] tracking-tight text-text sm:text-5xl lg:text-6xl">
          Turn every competitor&apos;s ad library into a ranked,{" "}
          <span className="italic font-normal text-text">searchable</span> intelligence engine.
        </h1>

        <p className="mt-5 max-w-2xl text-pretty text-sm leading-relaxed text-text-muted sm:text-base md:text-lg">
          Helix scrapes live ad libraries on demand, scores visual hooks and copy angles, and closes the loop from discovery to your next winning brief.
        </p>

        {/* --- Primary & Secondary CTAs --- */}
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Button
            as={Link}
            to="/sign-up"
            variant="primary"
            size="lg"
            className="rounded-[4px] font-mono text-xs font-semibold uppercase tracking-wider"
          >
            Start 7-Day Free Trial
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>

          <Link
            to="/sign-in"
            className="inline-flex items-center gap-1.5 font-mono text-xs font-medium uppercase tracking-wider text-text-muted transition-colors hover:text-text px-2 py-2"
          >
            Sign in to console
            <span className="text-text-faint">→</span>
          </Link>
        </div>

        {/* --- Visual Split: Product Loop (01-05) + Terminal / Phone Mockups --- */}
        <div className="mt-16 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-10 items-start">
          
          {/* Left Column: Numbered Product Loop 01-05 */}
          <div className="lg:col-span-5 flex flex-col justify-between h-full space-y-4">
            <div className="border border-border bg-surface rounded-[4px] p-5 md:p-6 divide-y divide-border/60">
              <div className="pb-3 mb-2 flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-accent-dim">
                  The Product Loop
                </span>
                <span className="font-mono text-[10px] text-text-faint">
                  01 → 05 PIPELINE
                </span>
              </div>

              {PRODUCT_STEPS.map((step) => (
                <div key={step.num} className="pt-3.5 pb-3.5 first:pt-2 last:pb-1 group">
                  <div className="flex items-baseline gap-3">
                    <span className="tnum font-mono text-xs font-medium text-text-faint shrink-0">
                      {step.num}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold uppercase tracking-wider text-text">
                          {step.label}
                        </span>
                        {step.isLast && (
                          <span className="inline-block h-1 w-6 bg-accent rounded-sm ml-1" />
                        )}
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-text-muted">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Micro Readout Bar */}
            <div className="grid grid-cols-3 gap-px overflow-hidden rounded-[4px] border border-border bg-border">
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <span className="label-mono">INDEXED</span>
                <span className="tnum font-mono text-sm font-medium text-text">14.2M+</span>
              </div>
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <span className="label-mono">P95 SPEED</span>
                <span className="tnum font-mono text-sm font-medium text-text">2.8s</span>
              </div>
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <span className="label-mono">PLATFORMS</span>
                <span className="tnum font-mono text-sm font-medium text-text">Meta · TikTok</span>
              </div>
            </div>
          </div>

          {/* Right Column: Illustrative Terminal + Mobile Mockup UI */}
          <div className="lg:col-span-7 flex flex-col gap-5">
            
            {/* Terminal Live-Status Card */}
            <div className="overflow-hidden rounded-[4px] border border-border bg-surface shadow-2xl">
              {/* Window Header (Flat, neutral dots) */}
              <div className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5" aria-hidden="true">
                    <span className="h-2 w-2 rounded-full bg-[#2a2a2a]" />
                    <span className="h-2 w-2 rounded-full bg-[#2a2a2a]" />
                    <span className="h-2 w-2 rounded-full bg-[#2a2a2a]" />
                  </div>
                  <span className="ml-2 font-mono text-[11px] text-text-muted">
                    helix-cli / live-discovery
                  </span>
                </div>
                <div className="flex items-center gap-1.5 font-mono text-[10.5px]">
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-accent shrink-0 animate-pulse"
                    style={{ boxShadow: "0 0 5px rgba(215, 255, 79, 0.7)" }}
                    aria-hidden="true"
                  />
                  <span className="text-text-muted">live</span>
                  <span className="text-text-faint ml-2 tnum">1.4s</span>
                </div>
              </div>

              {/* Terminal Content */}
              <div className="p-4 sm:p-5 font-mono text-[11.5px] leading-relaxed space-y-2">
                {/* Command */}
                <div className="flex items-center gap-2 text-text">
                  <span className="text-text-faint select-none">$</span>
                  <span>query &quot;nike running&quot; --country=US --depth=high</span>
                </div>

                {/* Dotted Leader Steps */}
                <div className="mt-3 space-y-1.5 text-text-muted">
                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">query parsing &amp; target verification</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className="tnum text-success shrink-0 font-medium">ok</span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">enumerating meta ad library corpus</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className="tnum text-success shrink-0 font-medium">ok</span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">extracting video assets &amp; transcripts</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className="tnum text-text font-medium shrink-0">142 ads</span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-accent shrink-0 w-4">→</span>
                    <span className="text-text">scoring visual hooks &amp; copy density</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className="tnum text-text font-medium shrink-0">18 winning</span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">synthesizing creative pattern brief</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className="tnum text-success shrink-0 font-medium">ok</span>
                  </div>
                </div>

                {/* Final Result Echo */}
                <div className="mt-3 pt-2.5 border-t border-border/80 flex items-center justify-between text-xs">
                  <span className="text-accent font-medium">
                    * 18 patterns discovered across 142 live creatives
                  </span>
                  <span className="tnum text-text-faint text-[10px]">
                    2.0 credits deducted
                  </span>
                </div>
              </div>
            </div>

            {/* Miniature Phone / Live Results UI Card */}
            <div className="overflow-hidden rounded-[4px] border border-border bg-surface-2 p-4 sm:p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded bg-surface flex items-center justify-center border border-border font-mono text-xs font-bold text-text">
                    N
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-semibold text-text">Nike Running (US)</h4>
                      <span className="font-mono text-[9px] uppercase tracking-wider bg-surface px-1.5 py-0.5 rounded border border-border text-text-muted">
                        Meta Ad Library
                      </span>
                    </div>
                    <p className="text-[11px] text-text-muted font-mono">142 active creatives · Updated 3m ago</p>
                  </div>
                </div>

                {/* Top Right Mini Sparkline */}
                <div className="flex items-center gap-2">
                  <span className="label-mono">VELOCITY</span>
                  <svg className="w-20 h-5" viewBox="0 0 80 20" fill="none">
                    <path
                      d="M2 16 L16 14 L30 17 L44 9 L58 11 L78 3"
                      stroke="#d7ff4f"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </div>

              {/* Miniature Creative Card Details */}
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                
                {/* Miniature Card 1 */}
                <div className="rounded-[4px] border border-border bg-surface p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[10px] text-accent-dim">HOOK PATTERN #01</span>
                    <span className="tnum font-mono text-[10px] font-semibold text-accent">94 / 100</span>
                  </div>
                  <p className="text-[11.5px] font-medium text-text leading-snug line-clamp-2">
                    &ldquo;Engineered for marathon recovery: How the Pegasus 41 cushions 20+ miles.&rdquo;
                  </p>
                  <div className="space-y-1 pt-1 font-mono text-[10px]">
                    <div className="flex justify-between text-text-muted">
                      <span>Visual Hook</span>
                      <span className="text-text">96%</span>
                    </div>
                    <div className="h-1 w-full rounded-full bg-[#242424] overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: "96%" }} />
                    </div>
                  </div>
                </div>

                {/* Miniature Card 2 */}
                <div className="rounded-[4px] border border-border bg-surface p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[10px] text-accent-dim">HOOK PATTERN #02</span>
                    <span className="tnum font-mono text-[10px] font-semibold text-accent">89 / 100</span>
                  </div>
                  <p className="text-[11.5px] font-medium text-text leading-snug line-clamp-2">
                    &ldquo;Stop heel striking: 3 form cues Olympic coaches teach in week one.&rdquo;
                  </p>
                  <div className="space-y-1 pt-1 font-mono text-[10px]">
                    <div className="flex justify-between text-text-muted">
                      <span>Angle Density</span>
                      <span className="text-text">88%</span>
                    </div>
                    <div className="h-1 w-full rounded-full bg-[#242424] overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: "88%" }} />
                    </div>
                  </div>
                </div>

              </div>

              {/* Bottom Live Status Pill */}
              <div className="mt-3.5 pt-2.5 border-t border-border flex items-center justify-between">
                <div className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-full bg-accent animate-pulse"
                    style={{ boxShadow: "0 0 6px rgba(215, 255, 79, 0.7)" }}
                    aria-hidden="true"
                  />
                  <span className="font-mono text-[10px] font-semibold tracking-wider text-text uppercase">
                    Live Corpus Stream
                  </span>
                </div>
                <span className="font-mono text-[10px] text-text-muted">
                  Scored via LLM Heuristics
                </span>
              </div>

            </div>

          </div>

        </div>

      </div>
    </section>
  )
}
