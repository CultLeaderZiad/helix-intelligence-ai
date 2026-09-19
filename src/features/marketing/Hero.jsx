import { useState, useEffect, useMemo, useRef } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Sparkles, Check, TrendingUp, Layers, Zap, Eye, Terminal as TerminalIcon, Activity } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

/**
 * =======================================================================
 * MARKETING HERO SECTION — Real-Time Instrument Simulation Engine
 * =======================================================================
 * Illustrative real-time CLI terminal and creative scorecard with
 * moving numbers, live competitor stream updates, and stage progressions.
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

const COMPETITOR_SCENARIOS = [
  {
    brandName: "Nike Running (US)",
    brandInitial: "N",
    platformTag: "Meta Ad Library",
    cmd: 'query "nike running" --country=US --depth=high',
    activeCreatives: 142,
    winningPatterns: 18,
    elapsed: "1.4s",
    credits: "2.0",
    sparkline: "M2 16 L16 14 L30 17 L44 9 L58 11 L78 3",
    pattern1: {
      tag: "HOOK PATTERN #01",
      score: "94 / 100",
      headline: "“Engineered for marathon recovery: How the Pegasus 41 cushions 20+ miles.”",
      metricName: "Visual Hook",
      metricVal: "96%",
    },
    pattern2: {
      tag: "HOOK PATTERN #02",
      score: "89 / 100",
      headline: "“Stop heel striking: 3 form cues Olympic coaches teach in week one.”",
      metricName: "Angle Density",
      metricVal: "88%",
    },
    competitorUpdate: "Nike retired 3 fatigue variants · Scaled 5 UGC marathon angles (2m ago)",
  },
  {
    brandName: "Gymshark Studio (UK)",
    brandInitial: "G",
    platformTag: "TikTok Creative Center",
    cmd: 'query "gymshark training" --country=GB --depth=deep',
    activeCreatives: 186,
    winningPatterns: 24,
    elapsed: "1.1s",
    credits: "2.5",
    sparkline: "M2 18 L16 12 L30 15 L44 7 L58 6 L78 2",
    pattern1: {
      tag: "HOOK PATTERN #01",
      score: "97 / 100",
      headline: "“Why gym lifters are cutting sleeves: The seamless drop-arm cut explained.”",
      metricName: "Visual Hook",
      metricVal: "98%",
    },
    pattern2: {
      tag: "HOOK PATTERN #02",
      score: "92 / 100",
      headline: "“Lifting straps vs bare grip: Real grip friction testing on 500lb deadlift.”",
      metricName: "Angle Density",
      metricVal: "93%",
    },
    competitorUpdate: "Gymshark launched 12 high-velocity TikTok creator scripts (3m ago)",
  },
  {
    brandName: "Alo Yoga Active (US)",
    brandInitial: "A",
    platformTag: "Meta & TikTok",
    cmd: 'query "alo yoga sets" --country=US --depth=high',
    activeCreatives: 214,
    winningPatterns: 31,
    elapsed: "1.6s",
    credits: "2.5",
    sparkline: "M2 15 L16 16 L30 11 L44 13 L58 5 L78 2",
    pattern1: {
      tag: "HOOK PATTERN #01",
      score: "96 / 100",
      headline: "“Studio to street: 4 ways to style the Airlift high-waist set for fall.”",
      metricName: "Visual Hook",
      metricVal: "95%",
    },
    pattern2: {
      tag: "HOOK PATTERN #02",
      score: "91 / 100",
      headline: "“Hot flow test: 90-minute moisture-wicking and slip durability review.”",
      metricName: "Angle Density",
      metricVal: "90%",
    },
    competitorUpdate: "Alo Yoga shifted +65% spend into TikTok organic-style Reels (1m ago)",
  },
  {
    brandName: "AG1 Athletics (US)",
    brandInitial: "A",
    platformTag: "Meta Ad Library",
    cmd: 'query "ag1 morning routine" --country=US --depth=full',
    activeCreatives: 168,
    winningPatterns: 22,
    elapsed: "1.3s",
    credits: "2.0",
    sparkline: "M2 17 L16 13 L30 14 L44 8 L58 7 L78 2",
    pattern1: {
      tag: "HOOK PATTERN #01",
      score: "95 / 100",
      headline: "“The 60-second morning habit: Why Dr. Huberman drinks AG1 cold on waking.”",
      metricName: "Visual Hook",
      metricVal: "97%",
    },
    pattern2: {
      tag: "HOOK PATTERN #02",
      score: "90 / 100",
      headline: "“75 vitamins in 1 scoop: Breaking down the gut biome absorption list.”",
      metricName: "Angle Density",
      metricVal: "89%",
    },
    competitorUpdate: "AG1 testing 8 founder podcast hooks against scientific breakdown ads (4m ago)",
  },
]

export function Hero() {
  const [scenarioIdx, setScenarioIdx] = useState(0)
  const [streamStage, setStreamStage] = useState(5) // 1..5 for steps
  const [displayedCreatives, setDisplayedCreatives] = useState(142)
  const [displayedWinners, setDisplayedWinners] = useState(18)
  const [indexedCounter, setIndexedCounter] = useState(14249180)
  const currentScenario = COMPETITOR_SCENARIOS[scenarioIdx]

  // Scenario auto-cycling & stage animation
  useEffect(() => {
    let stageTimer
    let step = 1
    setStreamStage(1)
    setDisplayedCreatives(Math.round(currentScenario.activeCreatives * 0.4))
    setDisplayedWinners(Math.round(currentScenario.winningPatterns * 0.3))

    const advanceStage = () => {
      step += 1
      if (step <= 5) {
        setStreamStage(step)
        if (step === 3) {
          setDisplayedCreatives(currentScenario.activeCreatives)
        }
        if (step === 4) {
          setDisplayedWinners(currentScenario.winningPatterns)
        }
        stageTimer = setTimeout(advanceStage, 600)
      } else {
        // Complete stage hold, then switch scenario
        stageTimer = setTimeout(() => {
          setScenarioIdx((prev) => (prev + 1) % COMPETITOR_SCENARIOS.length)
        }, 3200)
      }
    }

    stageTimer = setTimeout(advanceStage, 500)

    return () => clearTimeout(stageTimer)
  }, [scenarioIdx])

  // Live ticking micro-counter for indexed corpus
  useEffect(() => {
    const counterInterval = setInterval(() => {
      setIndexedCounter((prev) => prev + Math.floor(Math.random() * 4) + 1)
    }, 2400)
    return () => clearInterval(counterInterval)
  }, [])

  return (
    <section className="grid-backdrop relative border-b border-border bg-bg overflow-hidden min-h-[600px]">
      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col px-4 py-20 md:px-6 md:py-32">
        
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
        <h1 className="mt-6 max-w-4xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight text-text sm:text-6xl lg:text-7xl">
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

        {/* --- Visual Split: Product Loop (01-05) + Terminal / Moving Numbers Mockups --- */}
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

            {/* Micro Readout Bar with LIVE Ticking Counters */}
            <div className="grid grid-cols-3 gap-px overflow-hidden rounded-[4px] border border-border bg-border">
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <div className="flex items-center justify-between">
                  <span className="label-mono">INDEXED</span>
                  <span className="h-1 w-1 rounded-full bg-accent animate-ping" />
                </div>
                <span className="tnum font-mono text-sm font-medium text-text transition-all">
                  {(indexedCounter / 1000000).toFixed(2)}M+
                </span>
              </div>
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <span className="label-mono">P95 SPEED</span>
                <span className="tnum font-mono text-sm font-medium text-accent">
                  {currentScenario.elapsed}
                </span>
              </div>
              <div className="flex flex-col gap-1 bg-surface px-3.5 py-2.5">
                <span className="label-mono">PLATFORMS</span>
                <span className="tnum font-mono text-sm font-medium text-text">Meta · TikTok</span>
              </div>
            </div>
          </div>

          {/* Right Column: Live Streaming Terminal + Moving Dashboard Numbers */}
          <div className="lg:col-span-7 flex flex-col gap-5">
            
            {/* Terminal Live-Status Card */}
            <div className="overflow-hidden rounded-[4px] border border-border bg-surface shadow-2xl">
              {/* Window Header */}
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
                  <span className="text-accent ml-2 tnum font-semibold">{currentScenario.elapsed}</span>
                </div>
              </div>

              {/* Terminal Content with Stage Flow */}
              <div className="p-4 sm:p-5 font-mono text-[11.5px] leading-relaxed space-y-2">
                {/* Dynamic Command */}
                <div className="flex items-center gap-2 text-text">
                  <span className="text-text-faint select-none">$</span>
                  <span className="text-white font-medium transition-colors">
                    {currentScenario.cmd}
                  </span>
                </div>

                {/* Dotted Leader Steps with Live Progress */}
                <div className="mt-3 space-y-1.5 text-text-muted">
                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">query parsing &amp; target verification</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className={cn("tnum shrink-0 font-medium", streamStage >= 1 ? "text-success" : "text-text-faint")}>
                      {streamStage >= 1 ? "ok" : "..."}
                    </span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">enumerating meta ad library corpus</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className={cn("tnum shrink-0 font-medium", streamStage >= 2 ? "text-success" : "text-text-faint")}>
                      {streamStage >= 2 ? "ok" : "..."}
                    </span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">extracting video assets &amp; transcripts</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className={cn("tnum font-medium shrink-0 transition-all", streamStage >= 3 ? "text-text" : "text-text-faint")}>
                      {streamStage >= 3 ? `${displayedCreatives} ads` : "fetching..."}
                    </span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-accent shrink-0 w-4">→</span>
                    <span className="text-text">scoring visual hooks &amp; copy density</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className={cn("tnum font-medium shrink-0 transition-all", streamStage >= 4 ? "text-accent font-semibold" : "text-text-faint")}>
                      {streamStage >= 4 ? `${displayedWinners} winning` : "scoring..."}
                    </span>
                  </div>

                  <div className="flex items-baseline">
                    <span className="text-text-faint shrink-0 w-4">→</span>
                    <span className="text-text">synthesizing creative pattern brief</span>
                    <span className="mx-2 min-w-4 flex-1 self-center border-b border-dotted border-border-strong" aria-hidden="true" />
                    <span className={cn("tnum shrink-0 font-medium", streamStage >= 5 ? "text-success" : "text-text-faint")}>
                      {streamStage >= 5 ? "ok" : "..."}
                    </span>
                  </div>
                </div>

                {/* Final Result Echo */}
                <div className="mt-3 pt-2.5 border-t border-border/80 flex items-center justify-between text-xs">
                  <span className={cn("font-medium transition-colors", streamStage >= 5 ? "text-accent" : "text-text-muted")}>
                    * {displayedWinners} patterns discovered across {displayedCreatives} live creatives
                  </span>
                  <span className="tnum text-text-faint text-[10px]">
                    {currentScenario.credits} credits deducted
                  </span>
                </div>
              </div>
            </div>

            {/* Moving Dashboard Card: Real-Time Competitor Activity & Metrics */}
            <div className="overflow-hidden rounded-[4px] border border-border bg-surface-2 p-4 sm:p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded bg-surface flex items-center justify-center border border-accent/40 font-mono text-xs font-bold text-accent shadow-sm shadow-accent/20">
                    {currentScenario.brandInitial}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-semibold text-text">{currentScenario.brandName}</h4>
                      <span className="font-mono text-[9px] uppercase tracking-wider bg-surface px-1.5 py-0.5 rounded border border-border text-text-muted">
                        {currentScenario.platformTag}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-muted font-mono">
                      <span className="text-accent font-semibold">{displayedCreatives}</span> active creatives · Updated just now
                    </p>
                  </div>
                </div>

                {/* Top Right Mini Sparkline with Animated Undulation */}
                <div className="flex items-center gap-2">
                  <span className="label-mono">VELOCITY</span>
                  <svg className="w-20 h-5" viewBox="0 0 80 20" fill="none">
                    <path
                      d={currentScenario.sparkline}
                      stroke="#d7ff4f"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="transition-all duration-700"
                    />
                  </svg>
                </div>
              </div>

              {/* Moving Hook Pattern Cards */}
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                
                {/* Pattern Card 1 */}
                <div className="rounded-[4px] border border-border bg-surface p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[10px] text-accent-dim">{currentScenario.pattern1.tag}</span>
                    <span className="tnum font-mono text-[10px] font-semibold text-accent">{currentScenario.pattern1.score}</span>
                  </div>
                  <p className="text-[11.5px] font-medium text-text leading-snug line-clamp-2 min-h-[32px]">
                    {currentScenario.pattern1.headline}
                  </p>
                  <div className="space-y-1 pt-1 font-mono text-[10px]">
                    <div className="flex justify-between text-text-muted">
                      <span>{currentScenario.pattern1.metricName}</span>
                      <span className="text-text font-semibold">{currentScenario.pattern1.metricVal}</span>
                    </div>
                    <div className="h-1 w-full rounded-full bg-[#242424] overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all duration-700"
                        style={{ width: currentScenario.pattern1.metricVal }}
                      />
                    </div>
                  </div>
                </div>

                {/* Pattern Card 2 */}
                <div className="rounded-[4px] border border-border bg-surface p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[10px] text-accent-dim">{currentScenario.pattern2.tag}</span>
                    <span className="tnum font-mono text-[10px] font-semibold text-accent">{currentScenario.pattern2.score}</span>
                  </div>
                  <p className="text-[11.5px] font-medium text-text leading-snug line-clamp-2 min-h-[32px]">
                    {currentScenario.pattern2.headline}
                  </p>
                  <div className="space-y-1 pt-1 font-mono text-[10px]">
                    <div className="flex justify-between text-text-muted">
                      <span>{currentScenario.pattern2.metricName}</span>
                      <span className="text-text font-semibold">{currentScenario.pattern2.metricVal}</span>
                    </div>
                    <div className="h-1 w-full rounded-full bg-[#242424] overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all duration-700"
                        style={{ width: currentScenario.pattern2.metricVal }}
                      />
                    </div>
                  </div>
                </div>

              </div>

              {/* Bottom Live Competitor Stream & Diff Ticker */}
              <div className="mt-3.5 pt-2.5 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-full bg-accent animate-pulse shrink-0"
                    style={{ boxShadow: "0 0 6px rgba(215, 255, 79, 0.7)" }}
                    aria-hidden="true"
                  />
                  <span className="font-mono text-[10px] font-semibold tracking-wider text-accent uppercase">
                    Live Corpus Stream
                  </span>
                </div>
                <div className="font-mono text-[10.5px] text-text-muted truncate max-w-md">
                  <span className="text-text-faint">DIFF:</span> {currentScenario.competitorUpdate}
                </div>
              </div>

            </div>

          </div>

        </div>

      </div>
    </section>
  )
}

