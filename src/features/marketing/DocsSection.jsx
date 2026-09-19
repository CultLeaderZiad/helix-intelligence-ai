import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/Button"

/**
 * Docs teaser. The technical voice earns a real artifact: a mono terminal
 * block showing a discovery run as an API call, because every loop in the
 * console is one. Kept as a template string so the JSON braces never hit the
 * JSX parser.
 */
const SNIPPET = `$ curl -X POST https://api.helix.io/api/discovery/jobs \\
    -H "X-API-Key: $HELIX_KEY" \\
    -d '{ "query": "dtc skincare", "sort": "composite_desc" }'

{
  "job_id": "job_01j7b9k2x4p0m",
  "status": "in_progress",
  "progress": 0.25,
  "stage": "targeting_ad_libraries",
  "stage_label": "Targeting verified ad libraries",
  "records_found": 0,
  "elapsed_ms": 420
} `

export function DocsSection() {
  return (
    <section id="docs" className="scroll-mt-16 border-b border-border bg-bg relative overflow-hidden">
      <div className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 gap-10 px-4 py-20 md:grid-cols-2 md:px-6">
        <div className="flex flex-col gap-3 md:pt-4">
          <span className="font-mono text-[10px] uppercase leading-none tracking-[0.14em] text-accent-dim">
            Docs
          </span>
          <h2 className="text-balance text-2xl font-medium tracking-tight text-text md:text-3xl">
            Built to be driven by machines, too.
          </h2>
          <p className="text-pretty text-sm leading-relaxed text-text-muted">
            Every loop in the console is an API call. Enqueue a scrape, poll the
            job, and pull ranked records straight into your own pipeline —
            webhooks included.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button as={Link} to="/docs" variant="primary" size="lg">
              Explore Docs
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <Button as={Link} to="/sign-up" variant="outline" size="lg">
              Get an API key
            </Button>
          </div>
        </div>

        <div className="overflow-hidden rounded-sm border border-border bg-surface">
          <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-3 py-2">
            <span className="label-mono">POST /api/discovery/jobs</span>
            <span className="ml-auto label-mono text-accent-dim">200 ok</span>
          </div>
          <pre className="overflow-x-auto px-4 py-4">
            <code className="font-mono text-[12px] leading-relaxed text-text-muted">
              {SNIPPET}
            </code>
          </pre>
        </div>
      </div>
    </section>
  )
}
