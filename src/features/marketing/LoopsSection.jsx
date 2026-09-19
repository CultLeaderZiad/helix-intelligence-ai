import React, { useState } from "react"
import { cn } from "@/lib/utils"
import { NAV_SECTIONS } from "@/app/navigation"
import CardSwap, { Card } from "@/components/ui/CardSwap"
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
  Eye,
  Check
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
    <section id="product" className="scroll-mt-16 border-b border-border bg-bg overflow-hidden py-16 sm:py-20 lg:py-28 relative">
      {/* Subtle background ambient glow */}
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
          
          {/* Left Column: Product Positioning & Interactive Features */}
          <div className="lg:col-span-5 flex flex-col gap-6 z-10">
            <div className="space-y-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-accent/30 bg-accent/10 font-mono text-[11px] uppercase tracking-[0.14em] text-accent font-semibold">
                <Layers className="h-3.5 w-3.5" />
                The Product
              </span>
              <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold tracking-tight text-text leading-tight">
                Four loops, <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent via-white to-text-muted">
                  one instrument.
                </span>
              </h2>
              <p className="text-sm sm:text-base leading-relaxed text-text-muted">
                Discovery feeds intelligence, intelligence briefs creation, and live performance feeds back into scoring.
                The output of each loop is the input to the next.
              </p>
            </div>

            {/* Interactive Loop Feature List */}
            <div className="space-y-2.5 pt-1">
              {loops.map((loop, idx) => {
                const Icon = loop.icon
                const isSelected = activeCardIndex === idx
                return (
                  <div
                    key={loop.key}
                    onClick={() => setActiveCardIndex(idx)}
                    className={cn(
                      "flex items-start gap-3.5 p-3 sm:p-3.5 rounded-xl border transition-all cursor-pointer group select-none",
                      isSelected
                        ? "bg-gradient-to-r from-accent/15 via-surface-2 to-surface border-accent/60 shadow-lg shadow-accent/10 translate-x-1"
                        : "bg-surface/50 border-border/70 hover:border-border-strong hover:bg-surface text-text-muted hover:text-text"
                    )}
                  >
                    <span className={cn(
                      "font-mono text-xs font-bold pt-0.5 transition-colors",
                      isSelected ? "text-accent" : "text-text-muted"
                    )}>
                      {loop.num}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className={cn(
                          "text-xs sm:text-sm font-bold flex items-center gap-2 transition-colors",
                          isSelected ? "text-white" : "text-text"
                        )}>
                          <Icon className={cn("h-4 w-4 transition-colors", isSelected ? "text-accent" : "text-text-muted")} />
                          {loop.title}
                        </span>
                        <span className={cn(
                          "text-[10px] font-mono uppercase px-2 py-0.5 rounded border transition-colors shrink-0",
                          isSelected
                            ? "border-accent/40 bg-accent/10 text-accent font-semibold"
                            : "border-border bg-surface-elevated text-text-faint"
                        )}>
                          {loop.tag}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed mt-1 line-clamp-1">
                        {loop.desc}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Quick Action Link */}
            <div className="pt-1">
              <a
                href="/create"
                className="inline-flex items-center gap-2 text-xs sm:text-sm font-mono text-accent hover:underline font-medium"
              >
                <span>Launch Creative Studio in Console</span>
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Right Column: React Bits CardSwap Component Canvas */}
          <div className="lg:col-span-7 relative flex items-center justify-center min-h-[470px] sm:min-h-[520px] lg:min-h-[560px] w-full overflow-visible">
            <div className="w-full relative flex items-center justify-center overflow-visible py-2">
              <CardSwap
                width={580}
                height={450}
                delay={2800}
                pauseOnHover={true}
                activeCardIndex={activeCardIndex}
                onActiveChange={(newIdx) => setActiveCardIndex(newIdx)}
                onCardClick={(idx) => setActiveCardIndex(idx)}
              >
                {/* ============================================================ */}
                {/* CARD 0: DISCOVER ENGINE (Loop 01) */}
                {/* ============================================================ */}
                <Card className="bg-[#0e1115] border border-white/10 p-4 sm:p-6 text-left flex flex-col justify-between shadow-2xl h-full">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-border/80 pb-2.5 sm:pb-3 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-cyan-400" />
                      </span>
                      <Compass className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-cyan-400 shrink-0" />
                      <span className="font-mono text-[11px] sm:text-xs lg:text-sm font-bold text-text truncate">
                        Discover &gt; Ad Mining
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 font-mono text-[9px] sm:text-[11px] font-semibold shrink-0">
                      327 Active Ads
                    </span>
                  </div>

                  {/* Query Bar */}
                  <div className="my-2 px-3.5 py-2 rounded-lg border border-border bg-surface-elevated/90 flex items-center justify-between text-xs font-mono">
                    <span className="text-text-muted">
                      Target Query: <strong className="text-white font-bold">"nike running"</strong>
                    </span>
                    <span className="text-cyan-300 text-[11px] font-semibold">Filtered: Meta + TikTok</span>
                  </div>

                  {/* Verified Platform Chips */}
                  <div className="p-2.5 rounded-lg border border-border/80 bg-surface/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
                      <span className="font-semibold text-text-faint">VERIFIED DATA SOURCES (6 PLATFORMS)</span>
                      <span className="text-accent font-semibold flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" /> Live Sync
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {["Meta Ad Library", "TikTok Creative Center", "Instagram", "X (Twitter)", "YouTube", "Kick"].map((p) => (
                        <span key={p} className="px-2 py-0.5 rounded border border-border bg-surface-elevated text-[10px] font-mono text-text-muted">
                          {p} ↗
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Top Winning Ad Unit Card */}
                  <div className="p-3 sm:p-3.5 rounded-xl border border-border bg-surface-2/90 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs sm:text-sm font-bold text-white">Nike Pegasus 41 — Global Campaign</span>
                      <span className="px-2 py-0.5 rounded border border-accent/40 bg-accent/15 text-accent font-mono text-[11px] font-extrabold shadow-sm shadow-accent/20">
                        SCORE: 94.2
                      </span>
                    </div>
                    <p className="text-xs text-text-muted font-sans line-clamp-1 italic">
                      "Don't just run. Fly with responsive ReactX foam cushioning."
                    </p>
                    <div className="grid grid-cols-3 gap-2 pt-1 border-t border-border/50 text-[10px] sm:text-[11px] font-mono text-text-faint">
                      <div><span className="text-text-muted block text-[9px]">EST. REACH</span><strong className="text-text font-bold">1.4M</strong></div>
                      <div><span className="text-text-muted block text-[9px]">VELOCITY</span><strong className="text-accent font-bold">+340%/wk</strong></div>
                      <div><span className="text-text-muted block text-[9px]">LIFESPAN</span><strong className="text-text font-bold">42 Days</strong></div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/70 flex items-center justify-between text-[11px] font-mono text-text-faint">
                    <span>Ranked by Velocity & Durability</span>
                    <span className="text-cyan-300 font-bold flex items-center gap-1 hover:underline">
                      Mine Winning Patterns →
                    </span>
                  </div>
                </Card>

                {/* ============================================================ */}
                {/* CARD 1: INTELLIGENCE & PATTERNS (Loop 02) */}
                {/* ============================================================ */}
                <Card className="bg-[#0e1115] border border-white/10 p-4 sm:p-6 text-left flex flex-col justify-between shadow-2xl h-full">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-border/80 pb-2.5 sm:pb-3 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-purple-400" />
                      </span>
                      <Cpu className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-purple-400 shrink-0" />
                      <span className="font-mono text-[11px] sm:text-xs lg:text-sm font-bold text-text truncate">
                        Intelligence &gt; Patterns
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-300 font-mono text-[9px] sm:text-[11px] font-semibold shrink-0">
                      Mining 50+ Ads
                    </span>
                  </div>

                  <div className="space-y-2.5 py-1">
                    {/* Dominant Angle */}
                    <div className="p-2.5 sm:p-3 rounded-xl border border-purple-500/25 bg-purple-500/10 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                          <Sparkles className="h-3.5 w-3.5 text-purple-400" /> Dominant Hook Angle
                        </span>
                        <span className="text-[11px] font-mono text-purple-300 font-bold">88% Win Correlation</span>
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed">
                        Problem-agitation opening featuring slow-motion sole compression, transitioning directly to split-screen kinetic stress test.
                      </p>
                    </div>

                    {/* Signal Grid */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 sm:p-2.5 rounded-lg border border-border bg-surface text-xs font-mono">
                        <span className="text-text-faint block text-[9px] uppercase">FATIGUE RISK</span>
                        <span className="text-accent font-bold text-xs sm:text-sm">Low (Scaling)</span>
                      </div>
                      <div className="p-2 sm:p-2.5 rounded-lg border border-border bg-surface text-xs font-mono">
                        <span className="text-text-faint block text-[9px] uppercase">RECOMMENDED CTA</span>
                        <span className="text-white font-bold text-xs sm:text-sm">"Early Access"</span>
                      </div>
                    </div>

                    {/* Synthesis */}
                    <div className="p-2 sm:p-2.5 rounded-lg border border-border bg-surface/80 space-y-1">
                      <span className="text-[9px] font-mono text-text-faint uppercase font-semibold">Strategic Directive</span>
                      <p className="text-xs text-text-muted leading-relaxed line-clamp-2">
                        Competitors shifted +42% toward split-screen comparisons this week. Creative brief automatically calibrated for generation.
                      </p>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/70 flex items-center justify-between text-[11px] font-mono text-text-faint">
                    <span>Export Brief to Remix Studio</span>
                    <span className="text-purple-300 font-bold flex items-center gap-1 hover:underline">
                      1-Click Brief →
                    </span>
                  </div>
                </Card>

                {/* ============================================================ */}
                {/* CARD 2: REMIX & CREATE STUDIO (Loop 03) */}
                {/* ============================================================ */}
                <Card className="bg-[#0e1115] border border-white/10 p-4 sm:p-6 text-left flex flex-col justify-between shadow-2xl h-full">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-border/80 pb-2.5 sm:pb-3 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-accent" />
                      </span>
                      <PenTool className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-accent shrink-0" />
                      <span className="font-mono text-[11px] sm:text-xs lg:text-sm font-bold text-text truncate">
                        Create &gt; Remix Studio
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-accent/40 bg-accent/15 text-accent font-mono text-[9px] sm:text-[11px] font-semibold shrink-0">
                      Ratio: 1:1 Square
                    </span>
                  </div>

                  {/* Discovered Ad Banner */}
                  <div className="my-1 px-3 py-1.5 rounded-lg border border-border bg-surface-elevated flex items-center justify-between text-xs font-mono text-text-muted">
                    <span className="flex items-center gap-1.5 truncate">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                      Remix from Mined Nike Brief (5 ready)
                    </span>
                    <span className="text-accent text-xs font-semibold shrink-0">Switch ▾</span>
                  </div>

                  {/* Body Content Grid */}
                  <div className="grid grid-cols-12 gap-2 sm:gap-3 flex-1 items-stretch py-1">
                    {/* Controls Side */}
                    <div className="col-span-7 space-y-1.5 sm:space-y-2">
                      <div>
                        <span className="text-[9px] font-mono uppercase text-text-faint block mb-1 font-semibold">
                          Creative Style
                        </span>
                        <div className="grid grid-cols-2 gap-1 sm:gap-1.5">
                          <div className="p-1 sm:p-1.5 rounded-lg border border-accent bg-accent/15 text-[10px] sm:text-[11px] font-bold text-accent text-center">
                            Commercial 3D
                          </div>
                          <div className="p-1 sm:p-1.5 rounded-lg border border-border bg-surface text-[10px] sm:text-[11px] text-text-muted text-center">
                            Cinematic
                          </div>
                          <div className="p-1 sm:p-1.5 rounded-lg border border-border bg-surface text-[10px] sm:text-[11px] text-text-muted text-center">
                            Luxury
                          </div>
                          <div className="p-1 sm:p-1.5 rounded-lg border border-border bg-surface text-[10px] sm:text-[11px] text-text-muted text-center">
                            Split
                          </div>
                        </div>
                      </div>

                      {/* Aspect Ratio Row */}
                      <div>
                        <span className="text-[9px] font-mono uppercase text-text-faint block mb-1 font-semibold">
                          Deliverable Format
                        </span>
                        <div className="flex gap-1 sm:gap-1.5">
                          <span className="px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md border border-accent text-accent bg-accent/15 font-mono text-[9px] sm:text-[10px] font-bold">
                            1:1
                          </span>
                          <span className="px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md border border-border text-text-muted font-mono text-[9px] sm:text-[10px]">
                            9:16
                          </span>
                          <span className="px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md border border-border text-text-muted font-mono text-[9px] sm:text-[10px]">
                            16:9
                          </span>
                        </div>
                      </div>

                      {/* Prompt Chip */}
                      <div className="p-1.5 sm:p-2 rounded-lg bg-surface border border-border text-xs text-text-muted space-y-0.5 sm:space-y-1">
                        <span className="text-white font-bold flex items-center gap-1 text-[10px] sm:text-[11px]">
                          <Sparkles className="h-2.5 w-2.5 sm:h-3 sm:w-3 text-accent" /> Prompt
                        </span>
                        <p className="line-clamp-2 text-[9px] sm:text-[11px] text-text-faint font-mono">
                          "Studio commercial of obsidian sneaker on reflective pedestal, neon lime rim"
                        </p>
                      </div>
                    </div>

                    {/* Live Output Canvas Side */}
                    <div className="col-span-5 rounded-xl border border-border bg-black/80 p-2 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                      <div className="w-full h-full rounded-lg border border-dashed border-accent/40 flex flex-col items-center justify-center p-2 bg-gradient-to-b from-accent/5 to-surface-2/60">
                        <div className="h-10 w-10 sm:h-14 sm:w-14 rounded-full border border-accent/50 bg-accent/15 flex items-center justify-center mb-1.5 shadow-lg shadow-accent/20">
                          <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-accent" />
                        </div>
                        <span className="text-[11px] sm:text-xs font-mono font-bold text-white">
                          Commercial PNG
                        </span>
                        <span className="text-[9px] sm:text-[10px] font-mono text-accent font-semibold mt-0.5">
                          1024x1024 UHD
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/70 flex items-center justify-between text-[11px] font-mono text-text-faint">
                    <span>Dual-Engine AI Hubmix</span>
                    <span className="text-accent font-bold flex items-center gap-1 hover:underline">
                      GENERATE WITH HELIX AI →
                    </span>
                  </div>
                </Card>

                {/* ============================================================ */}
                {/* CARD 3: 24/7 COMPETITOR MONITORS (Loop 04) */}
                {/* ============================================================ */}
                <Card className="bg-[#0e1115] border border-white/10 p-4 sm:p-6 text-left flex flex-col justify-between shadow-2xl h-full">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-border/80 pb-2.5 sm:pb-3 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-emerald-400" />
                      </span>
                      <Radio className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-emerald-400 shrink-0" />
                      <span className="font-mono text-[11px] sm:text-xs lg:text-sm font-bold text-text truncate">
                        Monitors &gt; Diff Stream
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono text-[9px] sm:text-[11px] font-semibold shrink-0">
                      24/7 Crawl
                    </span>
                  </div>

                  {/* Activity Feed */}
                  <div className="space-y-2 py-1">
                    <div className="flex items-start gap-2.5 sm:gap-3 p-2 sm:p-2.5 rounded-xl border border-border bg-surface-2/90">
                      <span className="px-1.5 sm:px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono text-[9px] sm:text-[10px] font-bold mt-0.5 shrink-0">
                        NEW AD
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs sm:text-sm font-bold text-white">Shopify launched 3 new reels</div>
                        <p className="text-[11px] sm:text-xs text-text-muted truncate mt-0.5">Targeting boutique apparel and fashion retailers</p>
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint">2 hours ago · Automated</span>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5 sm:gap-3 p-2 sm:p-2.5 rounded-xl border border-border bg-surface-2/90">
                      <span className="px-1.5 sm:px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono text-[9px] sm:text-[10px] font-bold mt-0.5 shrink-0">
                        DIFF
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs sm:text-sm font-bold text-white">Gymshark headline shifted</div>
                        <p className="text-[11px] sm:text-xs text-text-muted truncate mt-0.5">Changed: "Summer Launch" → "Restocked: Black Camo"</p>
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint">5 hours ago · Copy test</span>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5 sm:gap-3 p-2 sm:p-2.5 rounded-xl border border-border bg-surface-2/90">
                      <span className="px-1.5 sm:px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 font-mono text-[9px] sm:text-[10px] font-bold mt-0.5 shrink-0">
                        KILLED
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs sm:text-sm font-bold text-white">Nike discontinued static display</div>
                        <p className="text-[11px] sm:text-xs text-text-muted truncate mt-0.5">Killed after 9 days · Retained 68% velocity</p>
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint">Yesterday · Fatigue triggered</span>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/70 flex items-center justify-between text-[11px] font-mono text-text-faint">
                    <span>Baseline: 12 Brands</span>
                    <span className="text-emerald-300 font-bold flex items-center gap-1 hover:underline">
                      View Live Diffs →
                    </span>
                  </div>
                </Card>

                {/* ============================================================ */}
                {/* CARD 4: PERFORMANCE BENCHMARKING (Loop 05) */}
                {/* ============================================================ */}
                <Card className="bg-[#0e1115] border border-white/10 p-4 sm:p-6 text-left flex flex-col justify-between shadow-2xl h-full">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-border/80 pb-2.5 sm:pb-3 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-accent" />
                      </span>
                      <TrendingUp className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-accent shrink-0" />
                      <span className="font-mono text-[11px] sm:text-xs lg:text-sm font-bold text-text truncate">
                        Performance &gt; Scoring
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full border border-accent/40 bg-accent/15 text-accent font-mono text-[9px] sm:text-[11px] font-semibold shrink-0">
                      Model v2.4 Calibrated
                    </span>
                  </div>

                  <div className="space-y-2 sm:space-y-2.5 py-1">
                    {/* 3 Metric Tiles */}
                    <div className="grid grid-cols-3 gap-1.5 sm:gap-2 text-center">
                      <div className="p-2 sm:p-2.5 rounded-xl border border-border bg-surface">
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint block uppercase">TOP SCORE</span>
                        <span className="text-sm sm:text-lg font-extrabold text-accent">96.4</span>
                      </div>
                      <div className="p-2 sm:p-2.5 rounded-xl border border-border bg-surface">
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint block uppercase">ROAS MULT</span>
                        <span className="text-sm sm:text-lg font-extrabold text-white">3.8x</span>
                      </div>
                      <div className="p-2 sm:p-2.5 rounded-xl border border-border bg-surface">
                        <span className="text-[9px] sm:text-[10px] font-mono text-text-faint block uppercase">DURATION</span>
                        <span className="text-sm sm:text-lg font-extrabold text-white">38d</span>
                      </div>
                    </div>

                    {/* Leaderboard */}
                    <div className="p-2.5 sm:p-3 rounded-xl border border-border bg-surface/80 space-y-1.5 sm:space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
                        <span className="font-bold text-white">REACH LEADERBOARD</span>
                        <span className="text-accent font-semibold">EST. IMPRESSIONS</span>
                      </div>
                      <div className="space-y-1 sm:space-y-1.5 text-xs">
                        <div className="flex items-center justify-between py-0.5 sm:py-1 border-b border-border/50">
                          <span className="font-semibold text-white truncate mr-2">1. Nike — ReactX Launch</span>
                          <span className="font-mono text-accent font-bold shrink-0">2.8M</span>
                        </div>
                        <div className="flex items-center justify-between py-0.5 sm:py-1 border-b border-border/50">
                          <span className="font-semibold text-text truncate mr-2">2. Gymshark — Seamless</span>
                          <span className="font-mono text-text-muted shrink-0">1.6M</span>
                        </div>
                        <div className="flex items-center justify-between py-0.5 sm:py-1">
                          <span className="font-semibold text-text truncate mr-2">3. On Running — Monster 2</span>
                          <span className="font-mono text-text-muted shrink-0">1.1M</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-2 border-t border-border/70 flex items-center justify-between text-[11px] font-mono text-text-faint">
                    <span>Continuous Benchmark</span>
                    <span className="text-accent font-bold flex items-center gap-1 hover:underline">
                      Share Playbook →
                    </span>
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
