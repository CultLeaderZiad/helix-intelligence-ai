import React, { useState } from "react"
import { cn } from "@/lib/utils"
import { NAV_SECTIONS } from "@/app/navigation"
import CardSwap, { Card } from "@/components/ui/CardSwap"
import { PixelBlast } from "@/components/ui/PixelBlast"
import {
  Compass,
  Cpu,
  PenTool,
  Radio,
  TrendingUp,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Layers,
  Activity,
  CheckCircle2,
  Clock,
  Eye
} from "lucide-react"

export function LoopsSection() {
  const [activeCardIndex, setActiveCardIndex] = useState(0)

  const loops = [
    {
      num: "01",
      key: "discover",
      title: "Discover Engine",
      desc: "Scrape competitor ad libraries across Meta, TikTok, and X in real time.",
      icon: Compass,
      tag: "Live Pipeline"
    },
    {
      num: "02",
      key: "intelligence",
      title: "Intelligence & Patterns",
      desc: "Mine winning angles, script formulas, and fatigue curves across competitor creative.",
      icon: Cpu,
      tag: "Deep AI"
    },
    {
      num: "03",
      key: "create",
      title: "Remix & Create Studio",
      desc: "Generate high-fidelity, unwatermarked ad variations in 1:1, 4:5, 9:16, and 16:9.",
      icon: PenTool,
      tag: "Dual-Engine AI"
    },
    {
      num: "04",
      key: "monitors",
      title: "24/7 Competitor Monitors",
      desc: "Track competitor diffs: automatically catch new ads, killed ads, and copy adjustments.",
      icon: Radio,
      tag: "Automated Diffs"
    },
    {
      num: "05",
      key: "performance",
      title: "Performance & Scoring",
      desc: "Composite ad scoring and cross-brand reach leaderboards grounded in real data.",
      icon: TrendingUp,
      tag: "Benchmarking"
    }
  ]

  return (
    <section id="product" className="scroll-mt-16 border-b border-border bg-bg overflow-hidden py-20 lg:py-28 relative">
      {/* Interactive PixelBlast Ambient Background */}
      <div 
        className="pointer-events-none absolute inset-0 z-0 overflow-hidden opacity-40"
        aria-hidden="true"
      >
        <PixelBlast
          variant="diamond"
          pixelSize={2}
          color="#29e23f"
          patternScale={3}
          patternDensity={1.2}
          pixelSizeJitter={1.55}
          enableRipples
          rippleSpeed={0.4}
          rippleThickness={0.12}
          rippleIntensityScale={1.5}
          liquid
          liquidStrength={0.12}
          liquidRadius={1.2}
          liquidWobbleSpeed={5}
          speed={1.15}
          edgeFade={0.09}
        />
      </div>

      {/* Subtle background glow */}
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Product Positioning & Interactive Features */}
          <div className="lg:col-span-5 flex flex-col gap-6 z-10">
            <div className="space-y-3">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-accent/30 bg-accent/10 font-mono text-[11px] uppercase tracking-[0.14em] text-accent">
                <Layers className="h-3 w-3" />
                The Product
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text leading-tight">
                Four loops, <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent via-white to-text-muted">
                  one instrument.
                </span>
              </h2>
              <p className="text-sm leading-relaxed text-text-muted">
                Discovery feeds intelligence, intelligence briefs creation, and live performance feeds back into scoring.
                The output of each loop is the input to the next.
              </p>
            </div>

            {/* Interactive Loop Feature List */}
            <div className="space-y-2.5 pt-2">
              {loops.map((loop, idx) => {
                const Icon = loop.icon
                const isSelected = activeCardIndex === idx
                return (
                  <div
                    key={loop.key}
                    onClick={() => setActiveCardIndex(idx)}
                    className={cn(
                      "flex items-start gap-3.5 p-3 rounded-xl border transition-all cursor-pointer group",
                      isSelected
                        ? "bg-surface-2 border-accent/40 shadow-lg shadow-accent/5"
                        : "bg-surface/50 border-border/70 hover:border-border-strong hover:bg-surface"
                    )}
                  >
                    <span className="font-mono text-xs text-accent font-semibold pt-0.5">
                      {loop.num}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-text flex items-center gap-1.5">
                          <Icon className={cn("h-3.5 w-3.5", isSelected ? "text-accent" : "text-text-muted")} />
                          {loop.title}
                        </span>
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border border-border bg-surface-elevated text-text-faint">
                          {loop.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted leading-relaxed mt-0.5 line-clamp-1">
                        {loop.desc}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Quick Action Link */}
            <div className="pt-2">
              <a
                href="/create"
                className="inline-flex items-center gap-2 text-xs font-mono text-accent hover:underline"
              >
                <span>Launch Creative Studio in Console</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* Right Column: React Bits CardSwap Component Canvas */}
          <div className="lg:col-span-7 relative flex items-center justify-center min-h-[500px] sm:min-h-[580px] lg:min-h-[640px] w-full">
            <div className="w-full h-[540px] sm:h-[580px] relative flex items-center justify-center overflow-visible">
              <CardSwap
                width={520}
                height={420}
                cardDistance={55}
                verticalDistance={60}
                delay={4200}
                pauseOnHover={true}
                skewAmount={4}
                easing="elastic"
                onCardClick={(idx) => setActiveCardIndex(idx)}
              >
                {/* CARD 1: CREATE REMIX STUDIO (As requested by user from Create page) */}
                <Card className="bg-[#0e1013] border border-border/90 p-5 sm:p-6 text-left flex flex-col justify-between shadow-2xl">
                  {/* Top Window Header */}
                  <div className="flex items-center justify-between border-b border-border/70 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                      <span className="font-mono text-xs font-semibold text-text">
                        Helix &gt; Create &gt; Remix Studio
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-accent/30 bg-accent/10 text-accent font-mono text-[10px]">
                      Ratio: 1:1 Square
                    </span>
                  </div>

                  {/* Discovered Ad Banner */}
                  <div className="my-2 px-3 py-1.5 rounded-lg border border-border bg-surface-elevated/80 flex items-center justify-between text-[11px] font-mono text-text-muted">
                    <span className="flex items-center gap-1.5 truncate">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                      Remix from Discovered Ads ("elon musk") (5 available)
                    </span>
                    <span className="text-accent text-[10px] shrink-0">Pick Ad ▾</span>
                  </div>

                  {/* Body Content Grid */}
                  <div className="grid grid-cols-12 gap-3 flex-1 items-stretch py-1">
                    {/* Controls Side */}
                    <div className="col-span-7 space-y-2">
                      <div>
                        <span className="text-[9px] font-mono uppercase text-text-faint block mb-1">
                          Creative Style
                        </span>
                        <div className="grid grid-cols-2 gap-1.5">
                          <div className="p-1.5 rounded border border-accent bg-accent/10 text-[10px] font-medium text-accent">
                            Commercial Still
                          </div>
                          <div className="p-1.5 rounded border border-border bg-surface text-[10px] text-text-muted">
                            Quick Concept
                          </div>
                          <div className="p-1.5 rounded border border-border bg-surface text-[10px] text-text-muted">
                            Luxury Cinematic
                          </div>
                          <div className="p-1.5 rounded border border-border bg-surface text-[10px] text-text-muted">
                            Storyboard Frame
                          </div>
                        </div>
                      </div>

                      {/* Aspect Ratio Row */}
                      <div>
                        <span className="text-[9px] font-mono uppercase text-text-faint block mb-1">
                          Aspect Ratio Deliverable
                        </span>
                        <div className="flex gap-1">
                          <span className="px-2 py-0.5 rounded border border-accent text-accent bg-accent/10 font-mono text-[9px]">
                            1:1
                          </span>
                          <span className="px-2 py-0.5 rounded border border-border text-text-faint font-mono text-[9px]">
                            4:5
                          </span>
                          <span className="px-2 py-0.5 rounded border border-border text-text-faint font-mono text-[9px]">
                            9:16
                          </span>
                          <span className="px-2 py-0.5 rounded border border-border text-text-faint font-mono text-[9px]">
                            16:9
                          </span>
                        </div>
                      </div>

                      {/* Prompt formula chip */}
                      <div className="p-2 rounded bg-surface border border-border/80 text-[10px] text-text-muted space-y-1">
                        <span className="text-text font-semibold flex items-center gap-1">
                          <Sparkles className="h-2.5 w-2.5 text-accent" /> Hero Product Shot
                        </span>
                        <p className="line-clamp-2 text-[10px] text-text-faint font-mono">
                          "Clean studio commercial on matte obsidian stone with lime rim highlights"
                        </p>
                      </div>
                    </div>

                    {/* Live Output Canvas Side */}
                    <div className="col-span-5 rounded-lg border border-border bg-black/60 p-2 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                      <div className="w-full h-full rounded border border-dashed border-border-strong flex flex-col items-center justify-center p-2 bg-gradient-to-b from-surface/20 to-surface-2/40">
                        <div className="h-14 w-14 rounded-full border border-accent/40 bg-accent/10 flex items-center justify-center mb-2 shadow-lg shadow-accent/20">
                          <Sparkles className="h-6 w-6 text-accent" />
                        </div>
                        <span className="text-[10px] font-mono font-bold text-text">
                          Commercial PNG
                        </span>
                        <span className="text-[9px] font-mono text-accent">
                          1024x1024 · 0 Watermark
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-text-faint">
                    <span>Dual-Engine AI Hubmix Enabled</span>
                    <span className="text-accent">GENERATE WITH HELIX AI →</span>
                  </div>
                </Card>

                {/* CARD 2: DISCOVER ENGINE */}
                <Card className="bg-[#0e1013] border border-border/90 p-5 sm:p-6 text-left flex flex-col justify-between shadow-2xl">
                  <div className="flex items-center justify-between border-b border-border/70 pb-3">
                    <div className="flex items-center gap-2">
                      <Compass className="h-4 w-4 text-cyan-400" />
                      <span className="font-mono text-xs font-semibold text-text">
                        Discover &gt; Competitor Ad Mining
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-[10px]">
                      327 Active Ads Found
                    </span>
                  </div>

                  <div className="my-2 px-3 py-2 rounded-lg border border-border bg-surface-elevated/70 flex items-center justify-between text-xs font-mono text-text">
                    <span className="text-text-muted">Query: <strong className="text-text">"nike running"</strong></span>
                    <span className="text-cyan-400 text-[11px]">Filtered: Meta + TikTok</span>
                  </div>

                  {/* Creator / Entity Social Hub */}
                  <div className="p-2.5 rounded-lg border border-border/80 bg-surface/50 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
                      <span>VERIFIED PROFILES (6 PLATFORMS)</span>
                      <span className="text-accent">Live Sync</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {["X (Twitter)", "Instagram", "Kick", "Rumble", "YouTube", "TikTok"].map((p) => (
                        <span key={p} className="px-2 py-0.5 rounded border border-border bg-surface-elevated text-[9px] font-mono text-text-muted">
                          {p} ↗
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Ad Result Card */}
                  <div className="p-3 rounded-lg border border-border bg-surface-2 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-text">Nike Pegasus 41 Campaign</span>
                      <span className="px-1.5 py-0.5 rounded border border-accent/30 bg-accent/10 text-accent font-mono text-[10px] font-bold">
                        SCORE: 94.2
                      </span>
                    </div>
                    <p className="text-[11px] text-text-muted font-sans">
                      "Don't just run. Fly with responsive ReactX foam."
                    </p>
                    <div className="flex items-center gap-4 text-[10px] font-mono text-text-faint">
                      <span>EST. REACH: 1.4M</span>
                      <span>ACTIVE: 42 DAYS</span>
                      <span>FORMAT: IMAGE</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-text-faint">
                    <span>Ranked by Velocity & Creative Durability</span>
                    <span className="text-cyan-400">Mine Patterns →</span>
                  </div>
                </Card>

                {/* CARD 3: INTELLIGENCE & PATTERNS */}
                <Card className="bg-[#0e1013] border border-border/90 p-5 sm:p-6 text-left flex flex-col justify-between shadow-2xl">
                  <div className="flex items-center justify-between border-b border-border/70 pb-3">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-purple-400" />
                      <span className="font-mono text-xs font-semibold text-text">
                        Intelligence &gt; Pattern Extraction
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-400 font-mono text-[10px]">
                      Mining 50+ Creatives
                    </span>
                  </div>

                  <div className="space-y-2 py-1">
                    <div className="p-2.5 rounded-lg border border-purple-500/20 bg-purple-500/5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-text">Dominant Hook Angle</span>
                        <span className="text-[10px] font-mono text-purple-400">82% Correlation</span>
                      </div>
                      <p className="text-[11px] text-text-muted font-sans">
                        Problem-agitation opening featuring slow-motion sole compression, transitioning directly to sprint test.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 rounded border border-border bg-surface text-[11px] font-mono">
                        <span className="text-text-faint block text-[9px]">FATIGUE RISK</span>
                        <span className="text-accent font-semibold">Low (Scaling)</span>
                      </div>
                      <div className="p-2 rounded border border-border bg-surface text-[11px] font-mono">
                        <span className="text-text-faint block text-[9px]">RECOMMENDED CTA</span>
                        <span className="text-text font-semibold">"Unlock Trial"</span>
                      </div>
                    </div>

                    <div className="p-2 rounded border border-border bg-surface space-y-1">
                      <span className="text-[9px] font-mono text-text-faint uppercase">Strategy Synthesis</span>
                      <p className="text-[11px] text-text-muted line-clamp-2">
                        Competitors increased carousel frequency by 35% this week. Shift creative budget toward dynamic feature comparisons.
                      </p>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-text-faint">
                    <span>Export Brief to Remix Studio</span>
                    <span className="text-purple-400">1-Click Brief →</span>
                  </div>
                </Card>

                {/* CARD 4: MONITORS & DIFFS */}
                <Card className="bg-[#0e1013] border border-border/90 p-5 sm:p-6 text-left flex flex-col justify-between shadow-2xl">
                  <div className="flex items-center justify-between border-b border-border/70 pb-3">
                    <div className="flex items-center gap-2">
                      <Radio className="h-4 w-4 text-emerald-400" />
                      <span className="font-mono text-xs font-semibold text-text">
                        Monitors &gt; Competitor Diff Stream
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 font-mono text-[10px]">
                      24/7 Automated Crawl
                    </span>
                  </div>

                  <div className="space-y-2 py-1">
                    <div className="flex items-start gap-2.5 p-2 rounded-lg border border-border bg-surface-2">
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono text-[9px] font-bold mt-0.5">
                        NEW AD
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-text">Shopify launched 3 new reels</div>
                        <p className="text-[10px] text-text-muted truncate">Targeting boutique apparel and fashion retailers</p>
                        <span className="text-[9px] font-mono text-text-faint">2 hours ago</span>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5 p-2 rounded-lg border border-border bg-surface-2">
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-mono text-[9px] font-bold mt-0.5">
                        COPY DIFF
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-text">Gymshark headline shifted</div>
                        <p className="text-[10px] text-text-muted truncate">Changed from "Summer Launch" to "Restocked: Black Camo"</p>
                        <span className="text-[9px] font-mono text-text-faint">5 hours ago</span>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5 p-2 rounded-lg border border-border bg-surface-2">
                      <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 font-mono text-[9px] font-bold mt-0.5">
                        KILLED AD
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-text">Nike discontinued static display</div>
                        <p className="text-[10px] text-text-muted truncate">Killed after 9 days · Retained 68% velocity</p>
                        <span className="text-[9px] font-mono text-text-faint">Yesterday</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-text-faint">
                    <span>Baseline Tracking Configured</span>
                    <span className="text-emerald-400">View Live Diffs →</span>
                  </div>
                </Card>

                {/* CARD 5: PERFORMANCE BENCHMARKING */}
                <Card className="bg-[#0e1013] border border-border/90 p-5 sm:p-6 text-left flex flex-col justify-between shadow-2xl">
                  <div className="flex items-center justify-between border-b border-border/70 pb-3">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-accent" />
                      <span className="font-mono text-xs font-semibold text-text">
                        Performance &gt; Cross-Brand Scoring
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-accent/30 bg-accent/10 text-accent font-mono text-[10px]">
                      Model v2.4 Calibrated
                    </span>
                  </div>

                  <div className="space-y-2 py-1">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 rounded border border-border bg-surface">
                        <span className="text-[9px] font-mono text-text-faint block">TOP SCORE</span>
                        <span className="text-base font-bold text-accent">96.4</span>
                      </div>
                      <div className="p-2 rounded border border-border bg-surface">
                        <span className="text-[9px] font-mono text-text-faint block">ROAS MULTIPLIER</span>
                        <span className="text-base font-bold text-text">3.8x</span>
                      </div>
                      <div className="p-2 rounded border border-border bg-surface">
                        <span className="text-[9px] font-mono text-text-faint block">AVG DURATION</span>
                        <span className="text-base font-bold text-text">38d</span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded-lg border border-border bg-surface space-y-1.5">
                      <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
                        <span>REACH LEADERBOARD</span>
                        <span className="text-accent">EST. IMPRESSIONS</span>
                      </div>
                      <div className="space-y-1 text-xs">
                        <div className="flex items-center justify-between py-0.5 border-b border-border/40">
                          <span className="font-semibold text-text">1. Nike — ReactX Launch</span>
                          <span className="font-mono text-text-muted">2.8M (EST)</span>
                        </div>
                        <div className="flex items-center justify-between py-0.5 border-b border-border/40">
                          <span className="font-semibold text-text">2. Gymshark — Power Seamless</span>
                          <span className="font-mono text-text-muted">1.6M (EST)</span>
                        </div>
                        <div className="flex items-center justify-between py-0.5">
                          <span className="font-semibold text-text">3. On Running — Cloudmonster 2</span>
                          <span className="font-mono text-text-muted">1.1M (EST)</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-text-faint">
                    <span>1-Click Share as Public Playbook</span>
                    <span className="text-accent">Share Playbook →</span>
                  </div>
                </Card>
              </CardSwap>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default LoopsSection
