import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/Button"

/**
 * Landing hero. Same instrument-grade vocabulary as the app: hairline grid
 * backdrop, mono eyebrow, one lime primary action, and a readout strip that
 * borrows the app's status-bar treatment (mono labels, tabular numerals).
 * No gradient, no glass — a technical tool, stated plainly.
 */
const READOUTS = [
  { label: "Creatives indexed", value: "12.4M" },
  { label: "Ad libraries", value: "48" },
  { label: "Median scrape", value: "3.2s" },
  { label: "Scoring p95", value: "180ms" },
]

export function Hero() {
  return (
    <section className="grid-backdrop relative border-b border-border">
      <div className="mx-auto flex w-full max-w-6xl flex-col px-4 py-20 md:px-6 md:py-28">
        <span className="font-mono text-[10px] uppercase leading-none tracking-[0.14em] text-accent-dim">
          Competitive ad intelligence
        </span>

        <h1 className="mt-4 max-w-3xl text-balance text-3xl font-medium leading-[1.08] tracking-tight text-text md:text-5xl">
          Turn every competitor&apos;s ad library into a ranked, searchable
          corpus.
        </h1>

        <p className="mt-5 max-w-xl text-pretty text-sm leading-relaxed text-text-muted md:text-base">
          Helix scrapes live ad libraries on demand, scores every creative, and
          closes the loop from discovery to your next brief — one instrument,
          four loops.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button as={Link} to="/sign-up" variant="primary" size="lg">
            Get started
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
          <Button as={Link} to="/sign-in" variant="outline" size="lg">
            Sign in
          </Button>
        </div>

        <dl className="mt-14 grid max-w-3xl grid-cols-2 gap-px overflow-hidden rounded-sm border border-border bg-border md:grid-cols-4">
          {READOUTS.map((r) => (
            <div key={r.label} className="flex flex-col gap-1.5 bg-surface px-4 py-3.5">
              <dt className="label-mono">{r.label}</dt>
              <dd className="tnum font-mono text-lg font-medium leading-none text-text">
                {r.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
