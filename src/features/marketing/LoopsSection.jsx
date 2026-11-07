import { useState } from "react"
import { ArrowLeft, ArrowRight, Bookmark, Bot, Compass, Eye, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { useLanguage } from "@/context/LanguageContext"
import { useW8Copy } from "@/i18n/w8Product"
import CardSwap, { Card } from "@/components/ui/CardSwap"

const CARD_CLASS = "flex h-full flex-col justify-between gap-3 p-4 text-start sm:p-6"

/** @param {{ Icon: import("lucide-react").LucideIcon, title: string, chip: string }} props */
function CardHeader({ Icon, title, chip }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-border pb-3">
      <div className="flex min-w-0 items-center gap-2">
        <span className="relative flex h-2 w-2 shrink-0" aria-hidden="true">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60 motion-reduce:animate-none" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
        </span>
        <Icon className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <span className="truncate font-mono text-xs font-bold text-text sm:text-sm">{title}</span>
      </div>
      <span className="shrink-0 rounded-full border border-accent/40 bg-accent-wash px-2 py-0.5 font-mono text-[10px] font-semibold text-accent sm:text-[11px]">
        {chip}
      </span>
    </div>
  )
}

/** @param {{ children: React.ReactNode }} props */
function CardFooter({ children }) {
  return <p className="border-t border-border pt-2 font-mono text-[11px] text-text-faint">{children}</p>
}

/** @param {{ children: React.ReactNode }} props */
function Note({ children }) {
  return <p className="rounded-lg border border-border bg-surface/80 p-2.5 text-xs leading-relaxed text-text-muted">{children}</p>
}

/**
 * "Four loops, one instrument": the stacked, auto-swapping cards from the
 * live landing page, describing only the loops that exist today. No sample
 * brands, scores or counts: every card states a product rule.
 */
export function LoopsSection() {
  const { t, isRtl } = useLanguage()
  const c = useW8Copy()
  const [active, setActive] = useState(0)

  const loops = [
    { key: "discover", title: t("marketingDiscoverTitle"), desc: t("marketingDiscoverBody"), tag: c.loopDiscoverTag, Icon: Compass },
    { key: "monitors", title: t("marketingCreativeTitle"), desc: t("marketingCreativeBody"), tag: c.loopMonitorsTag, Icon: Eye },
    { key: "boards", title: t("marketingWorkspaceTitle"), desc: t("marketingWorkspaceBody"), tag: c.loopBoardsTag, Icon: Bookmark },
    { key: "agents", title: c.loopAgentsTitle, desc: c.loopAgentsBody, tag: c.loopAgentsTag, Icon: Bot },
  ]

  return (
    <section id="product" className="relative scroll-mt-20 overflow-hidden border-b border-border bg-bg py-16 sm:py-20 lg:py-28">
      <div className="pointer-events-none absolute end-1/4 top-1/2 h-96 w-96 -translate-y-1/2 rounded-full bg-accent/5 blur-3xl" aria-hidden="true" />

      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 items-center gap-8 px-4 md:px-6 lg:grid-cols-12 lg:gap-10">
        <div className="z-10 flex flex-col gap-6 lg:col-span-5">
          <div className="space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-wash px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
              <Layers className="h-3.5 w-3.5" aria-hidden="true" />
              {c.loopsLabel}
            </span>
            <h2 className="text-3xl font-extrabold leading-tight tracking-tight text-text sm:text-4xl lg:text-[42px]">
              {c.loopsTitleA}
              <br />
              <span className="bg-gradient-to-r from-accent via-white to-text-muted bg-clip-text text-transparent rtl:bg-gradient-to-l">
                {c.loopsTitleB}
              </span>
            </h2>
            <p className="text-sm leading-relaxed text-text-muted sm:text-base">{c.loopsIntro}</p>
          </div>

          <ul className="space-y-2.5" aria-label={c.loopsSwapHint}>
            {loops.map(({ key, title, desc, tag, Icon }, idx) => {
              const selected = active === idx
              return (
                <li key={key}>
                  <button
                    type="button"
                    onClick={() => setActive(idx)}
                    aria-pressed={selected}
                    className={cn(
                      "flex w-full items-start gap-3.5 rounded-xl border p-3 text-start transition-all sm:p-3.5",
                      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                      selected
                        ? "translate-x-1 border-accent/60 bg-gradient-to-r from-accent/15 via-surface to-surface shadow-lg shadow-accent/10 rtl:-translate-x-1 rtl:bg-gradient-to-l"
                        : "border-border bg-surface/50 text-text-muted hover:border-border-strong hover:bg-surface hover:text-text"
                    )}
                  >
                    <span className={cn("pt-0.5 font-mono text-xs font-bold", selected ? "text-accent" : "text-text-muted")}>
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 text-xs font-bold text-text sm:text-sm">
                          <Icon className={cn("h-4 w-4", selected ? "text-accent" : "text-text-muted")} aria-hidden="true" />
                          {title}
                        </span>
                        <span
                          className={cn(
                            "shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] uppercase",
                            selected ? "border-accent/40 bg-accent-wash font-semibold text-accent" : "border-border bg-surface text-text-faint"
                          )}
                        >
                          {tag}
                        </span>
                      </span>
                      <span className="mt-1 block text-xs leading-relaxed text-text-muted">{desc}</span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>

          <a href="#access" className="inline-flex items-center gap-2 font-mono text-xs font-medium text-accent hover:underline sm:text-sm">
            {c.loopsCta}
            {isRtl ? <ArrowLeft className="h-4 w-4" aria-hidden="true" /> : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
          </a>
        </div>

        <div className="relative flex min-h-[470px] w-full items-center justify-center overflow-visible sm:min-h-[520px] lg:col-span-7 lg:min-h-[560px]" dir="ltr">
          <CardSwap width={560} height={430} delay={3200} activeCardIndex={active} onActiveChange={setActive} onCardClick={setActive}>
            <Card className={CARD_CLASS} dir={isRtl ? "rtl" : "ltr"}>
              <CardHeader Icon={Compass} title={c.cardDiscoverTitle} chip={c.cardDiscoverChip} />
              <div className="space-y-2">
                <span className="block font-mono text-[10px] uppercase text-text-faint">{c.cardDiscoverPresets}</span>
                <div className="flex flex-wrap gap-1.5">
                  {[c.longevity30, c.longevity60, c.longevity90].map((label) => (
                    <span key={label} className="rounded-md border border-accent/40 bg-accent-wash px-2.5 py-1 font-mono text-[11px] font-bold text-accent">
                      {label}
                    </span>
                  ))}
                </div>
              </div>
              <Note>{c.cardDiscoverRunLength}</Note>
              <Note>{c.cardDiscoverScore}</Note>
              <Note>{c.cardDiscoverReach}</Note>
              <CardFooter>{c.cardDiscoverFooter}</CardFooter>
            </Card>

            <Card className={CARD_CLASS} dir={isRtl ? "rtl" : "ltr"}>
              <CardHeader Icon={Eye} title={c.cardMonitorsTitle} chip={c.cardMonitorsChip} />
              <div className="space-y-2">
                {[
                  [c.cardMonitorsNew, c.cardMonitorsNewBody, "border-success/30 bg-success/10 text-success"],
                  [c.cardMonitorsStopped, c.cardMonitorsStoppedBody, "border-danger/30 bg-danger/10 text-danger"],
                  [c.cardMonitorsRewritten, c.cardMonitorsRewrittenBody, "border-warning/30 bg-warning/10 text-warning"],
                ].map(([label, body, tone]) => (
                  <div key={label} className="flex items-start gap-3 rounded-xl border border-border bg-surface p-2.5">
                    <span className={cn("mt-0.5 shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase", tone)}>{label}</span>
                    <p className="text-xs leading-relaxed text-text-muted">{body}</p>
                  </div>
                ))}
              </div>
              <CardFooter>{c.cardMonitorsFooter}</CardFooter>
            </Card>

            <Card className={CARD_CLASS} dir={isRtl ? "rtl" : "ltr"}>
              <CardHeader Icon={Bookmark} title={c.cardBoardsTitle} chip={c.cardBoardsChip} />
              <Note>{c.cardBoardsSave}</Note>
              <div className="space-y-2 rounded-xl border border-accent/30 bg-accent-wash p-3">
                <span className="block font-mono text-[10px] uppercase text-accent">/b/…</span>
                <p className="text-xs leading-relaxed text-text">{c.cardBoardsLink}</p>
              </div>
              <Note>{c.cardBoardsTeam}</Note>
              <CardFooter>{c.cardBoardsFooter}</CardFooter>
            </Card>

            <Card className={CARD_CLASS} dir={isRtl ? "rtl" : "ltr"}>
              <CardHeader Icon={Bot} title={c.cardAgentsTitle} chip={c.cardAgentsChip} />
              <div className="space-y-1.5">
                <span className="block font-mono text-[10px] uppercase text-text-faint">{c.cardAgentsMarkdown}</span>
                <pre className="overflow-hidden rounded-lg border border-border bg-black/40 p-2.5 font-mono text-[11px] leading-relaxed text-text-muted" dir="ltr">
                  <span className="text-text-faint">GET</span> /api/discovery/stored-results{"\n"}
                  <span className="text-accent">Accept:</span> text/markdown
                </pre>
              </div>
              <div className="space-y-1.5">
                <span className="block font-mono text-[10px] uppercase text-text-faint">{c.cardAgentsMcp}</span>
                <div className="flex flex-wrap gap-1.5" dir="ltr">
                  {["search_ads", "get_board", "list_monitor_changes", "get_ad"].map((tool) => (
                    <span key={tool} className="rounded border border-border bg-surface px-2 py-0.5 font-mono text-[11px] text-text">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
              <CardFooter>{c.cardAgentsFooter}</CardFooter>
            </Card>
          </CardSwap>
        </div>
      </div>
    </section>
  )
}

export default LoopsSection
