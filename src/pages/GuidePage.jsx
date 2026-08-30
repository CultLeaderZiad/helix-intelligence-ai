import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { Button } from "@/components/ui/Button"
import {
  Radar,
  Network,
  PenLine,
  Activity,
  Bookmark,
  Shield,
  CreditCard,
  Sparkles,
  Zap,
  ArrowRight,
  Layers,
  Flame,
  Clock,
  CheckCircle2,
  HelpCircle,
  Code,
  Sliders,
  Database,
  Cpu
} from "lucide-react"

const GUIDE_STEPS = [
  {
    id: "overview",
    number: "00",
    title: "Helix Architecture & The 4 Loops",
    icon: Layers,
    badge: "Foundation",
    summary: "How Helix unifies competitor ad scraping, AI pattern synthesis, media generation, and performance feedback.",
    sections: [
      {
        heading: "The Helix Flywheel",
        text: "Helix operates as an instrument-grade intelligence loop designed for direct-response and performance marketing teams. The system connects 4 core operational loops in a continuous cycle:",
        bulletPoints: [
          "1. Discover — Enqueue ad library scrapes across Meta, Instagram, TikTok, and web sources.",
          "2. Intelligence — Mine winning hooks, emotional triggers, script structures, and angle packs.",
          "3. Create — Remix winning competitor patterns into net-new image & video assets using Higgsfield AI.",
          "4. Performance — Track creative longevity, fatigue curves, and feed survivor signals back into the scoring model."
        ]
      },
      {
        heading: "Trial Defaults & Credit Economics",
        text: "Helix enforces server-side credit limits with database row-level locking to protect external API quotas:",
        bulletPoints: [
          "Trial Plan: 25.0 initial credits upon signup (valid for 7 days).",
          "Daily Spend Limit: 3.5 credits/day for trial accounts (resets automatically at 00:00:00 UTC).",
          "Discover Search: 2.0 credits per query (cached for 12 hours per org for 0-credit repeats).",
          "Image Generation: 3.0 credits per Soul v2 still.",
          "Video Generation: 8.0 credits per DoP motion video.",
          "AI Creative Insight: 1.0 credit per deep LLM script teardown.",
          "Admin Role: Complete bypass of all credit and quota limits."
        ]
      }
    ]
  },
  {
    id: "discover",
    number: "01",
    title: "Discover — Competitor Ad Extraction",
    icon: Radar,
    badge: "Scraping & Ranking",
    summary: "Query competitor ad libraries with cost-aware fallback routing and 12-hour deduplication caching.",
    sections: [
      {
        heading: "Canonical Data Provider Order",
        text: "Discover uses an ordered, cost-aware canonical chain to provide fresh ads without wasteful API usage:",
        bulletPoints: [
          "1. Adyntel — Fast company/domain lookup for active digital ads.",
          "2. Apify Facebook Ad Library Actor — Broad ad enumeration and asset extraction.",
          "3. Meta Graph API — Official Facebook Ad Library boost (if configured).",
          "4. Bright Data Deep Fallback — Controlled deep fallback (+3.0 credits surcharge) only if earlier providers return 0 ads and balance permits.",
          "5. ScrapeGraph Enrichment — Automatically enriches top 2 landing pages for angle analysis."
        ]
      },
      {
        heading: "How to Execute Optimal Searches",
        text: "For the best discovery results:",
        bulletPoints: [
          "Search by Brand Domain (e.g., 'nike.com', 'hims.com') for comprehensive competitor catalog pulls.",
          "Search by Product Niche (e.g., 'ergonomic chair', 'collagen peptides') to benchmark industry leaders.",
          "Use the Filter Rail to isolate videos running >=14 days to surface evergreen scaling ads.",
          "Cached Queries: Succeeded searches are cached for 12 hours within your organization with zero credit charge."
        ]
      }
    ]
  },
  {
    id: "intelligence",
    number: "02",
    title: "Intelligence — Pattern Synthesis & Teardowns",
    icon: Network,
    badge: "LLM Analysis",
    summary: "Extract hook formulas, emotional triggers, script teardowns, and audience fatigue predictions.",
    sections: [
      {
        heading: "Pattern Packs Matrix",
        text: "Helix synthesizes recurring formulas across your discovered ad corpus:",
        bulletPoints: [
          "Hook Formulas: Identifies first-3-seconds hooks (Problem Agitation, Curiosity Gap, Shock Stat).",
          "Lift Index (+2.4x): Measures how much longer ads with this pattern survive compared to baseline.",
          "Emotional Resonance: Maps psychological triggers (Urgency, Social Proof, Fear of Missing Out, Authority)."
        ]
      },
      {
        heading: "Deep Creative Teardown",
        text: "Select any ad in Intelligence and click 'Generate Deep Teardown' (1.0 credit) to receive:",
        bulletPoints: [
          "Beat-by-Beat Narrative Breakdown: Opening visual, pain-point introduction, mechanism of action, CTA.",
          "Fatigue Forecast: Prediction of how many days remain before creative decay sets in.",
          "1-Click Remix: Export the extracted pattern directly into the Create Studio."
        ]
      }
    ]
  },
  {
    id: "create",
    number: "03",
    title: "Create Studio — Higgsfield Generation",
    icon: PenLine,
    badge: "Media Studio",
    summary: "Generate photorealistic commercial stills and motion ads with Higgsfield Soul v2 and DoP.",
    sections: [
      {
        heading: "Supported Generation Modes & Costs",
        text: "The Create Studio supports two primary media pipelines:",
        bulletPoints: [
          "Image Stills (3.0 credits): Premium Ad (Soul 2 commercial still), Quick Concept (fast ideation), Cinematic Ad (Soul Cinema dramatic lighting).",
          "Video Motion (8.0 credits): Quick Video (DoP Turbo social motion), Premium Video (DoP Standard commercial), Before → After (First/Last Frame transition).",
          "Aspect Ratios: 1:1 Square (Instagram/Feed), 9:16 Vertical (Stories/TikTok/Reels), 16:9 Landscape (YouTube/Desktop)."
        ]
      },
      {
        heading: "Remixing from Discovered Ads",
        text: "You can click 'Remix' on any ad in Discover, Intelligence, or Performance. Helix automatically passes the headline, hook score, and visual framing into the prompt brief for immediate remixing."
      }
    ]
  },
  {
    id: "performance",
    number: "04",
    title: "Performance — Longevity & Fatigue Tracking",
    icon: Activity,
    badge: "Analytics",
    summary: "Benchmark competitor ad durability, track evergreen survivor rates, and detect creative decay.",
    sections: [
      {
        heading: "Durability & Longevity Index",
        text: "In direct-response advertising, ad duration is the ultimate proxy for profitability. Advertisers do not keep unprofitable ads running.",
        bulletPoints: [
          "Evergreen Survivor (>=30 days): High-budget core scaling asset. Highest priority for remixing.",
          "Scaling Phase (14-29 days): Proven traction with positive ROAS.",
          "Testing Phase (<7 days): Initial competitor test variations.",
          "Format Share: Compare video vs static distribution across your competitor set."
        ]
      }
    ]
  },
  {
    id: "admin",
    number: "05",
    title: "Admin Center & Operations (Admins Only)",
    icon: Shield,
    badge: "Control Center",
    summary: "Manage organization limits, daily quotas, feature flags, user roles, and platform health.",
    sections: [
      {
        heading: "Admin Capabilities & Bypass",
        text: "Users with role='admin' have access to the Admin Center (/admin):",
        bulletPoints: [
          "Unlimited Quota Bypass: Admins bypass credit deduction checks and daily limits automatically.",
          "Organizations & Plans: Adjust credit balances, daily spend limits, or assign custom plans.",
          "Feature Flags: Toggle access to Discover, Intelligence, Create, Swipe Files, or Public API per org.",
          "Usage Metering: Inspect exact API usage, preflight logs, and provider breakdown."
        ]
      }
    ]
  }
]

export function GuidePage() {
  const navigate = useNavigate()
  const [activeStepId, setActiveStepId] = useState("overview")

  const currentStep = GUIDE_STEPS.find((s) => s.id === activeStepId) || GUIDE_STEPS[0]

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <BreadcrumbBar
        trail={["Helix", "Documentation", "Master Workflow Guide"]}
        meta="Step-by-Step Operating Playbook"
        actions={
          <Button size="xs" variant="primary" onClick={() => navigate("/discover")}>
            Open Discover Radar →
          </Button>
        }
      />

      <div className="flex-1 p-6 max-w-6xl mx-auto w-full space-y-6">
        
        {/* Header Hero */}
        <div className="rounded-lg border border-border bg-surface-2 p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-accent/10 px-2 py-0.5 font-mono text-[11px] font-bold text-accent uppercase border border-accent/20">
                  Helix User & Admin Manual
                </span>
                <span className="text-xs font-mono text-text-faint">v2.4 Production</span>
              </div>
              <h2 className="text-xl font-bold text-text mt-2">
                System Workflow, Loops & Credit Economics
              </h2>
              <p className="text-xs text-text-muted mt-1 max-w-2xl leading-relaxed">
                A complete sequence-by-sequence guide on how to search competitor ad libraries, extract AI intelligence, remix media with Higgsfield, and monitor creative longevity.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button size="xs" variant="outline" onClick={() => navigate("/intelligence")}>
                Intelligence Matrix
              </Button>
              <Button size="xs" variant="outline" onClick={() => navigate("/create")}>
                Create Studio
              </Button>
              <Button size="xs" variant="outline" onClick={() => navigate("/performance")}>
                Performance Radar
              </Button>
            </div>
          </div>
        </div>

        {/* Interactive Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          
          {/* Navigation Rail */}
          <div className="md:col-span-4 flex flex-col gap-2">
            <span className="label-mono text-text px-1">Playbook Sequence</span>
            <div className="flex flex-col gap-1.5">
              {GUIDE_STEPS.map((step) => {
                const isActive = step.id === activeStepId
                const Icon = step.icon
                return (
                  <button
                    key={step.id}
                    type="button"
                    onClick={() => setActiveStepId(step.id)}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-all ${
                      isActive
                        ? "border-accent bg-surface-3 text-text shadow-sm ring-1 ring-accent"
                        : "border-border bg-surface text-text-muted hover:border-border-strong hover:bg-surface-2 hover:text-text"
                    }`}
                  >
                    <span className="font-mono text-xs font-bold text-accent pt-0.5">
                      {step.number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <Icon className={`h-3.5 w-3.5 ${isActive ? "text-accent" : "text-text-faint"}`} />
                        <span className="text-xs font-bold text-text truncate">{step.title}</span>
                      </div>
                      <p className="text-[11px] text-text-muted mt-1 line-clamp-1">{step.summary}</p>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Step Detail Content */}
          <div className="md:col-span-8 flex flex-col gap-5 rounded-lg border border-border bg-surface p-6">
            
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-surface-2 border border-border text-accent">
                  <currentStep.icon className="h-5 w-5" />
                </div>
                <div>
                  <span className="rounded bg-surface-3 px-2 py-0.5 font-mono text-[10px] font-semibold text-accent border border-border">
                    {currentStep.badge}
                  </span>
                  <h3 className="text-lg font-bold text-text mt-1">{currentStep.title}</h3>
                </div>
              </div>

              <span className="font-mono text-xs text-text-faint">
                Module {currentStep.number} of 05
              </span>
            </div>

            <p className="text-xs text-text-muted font-mono leading-relaxed bg-surface-2 p-3 rounded border border-border/60">
              {currentStep.summary}
            </p>

            {/* Sections */}
            <div className="space-y-5">
              {currentStep.sections.map((sec, idx) => (
                <div key={idx} className="space-y-2">
                  <h4 className="text-xs font-bold font-mono text-accent uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                    {sec.heading}
                  </h4>
                  <p className="text-xs text-text leading-relaxed">
                    {sec.text}
                  </p>

                  {sec.bulletPoints && (
                    <ul className="space-y-1.5 pt-1">
                      {sec.bulletPoints.map((bp, bidx) => (
                        <li key={bidx} className="flex items-start gap-2 text-xs text-text-muted leading-relaxed">
                          <span className="font-mono text-accent text-[11px] font-bold">›</span>
                          <span>{bp}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>

            {/* Action Footer */}
            <div className="flex items-center justify-between border-t border-border pt-4 mt-2">
              <span className="text-[11px] text-text-faint font-mono">
                Need real-time execution?
              </span>
              <div className="flex items-center gap-2">
                {currentStep.id === "discover" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/discover")}>
                    Go to Discover Radar →
                  </Button>
                )}
                {currentStep.id === "intelligence" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/intelligence")}>
                    Go to Intelligence Matrix →
                  </Button>
                )}
                {currentStep.id === "create" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/create")}>
                    Go to Create Studio →
                  </Button>
                )}
                {currentStep.id === "performance" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/performance")}>
                    Go to Performance Radar →
                  </Button>
                )}
                {currentStep.id === "admin" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/admin")}>
                    Open Admin Center →
                  </Button>
                )}
                {currentStep.id === "overview" && (
                  <Button size="xs" variant="primary" onClick={() => navigate("/discover")}>
                    Start Operating →
                  </Button>
                )}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  )
}

export default GuidePage
