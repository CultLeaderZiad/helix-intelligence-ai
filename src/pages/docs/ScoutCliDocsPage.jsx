import React, { useState } from "react"
import { Link } from "react-router-dom"
import { Terminal, ArrowLeft, Download, Shield, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/Button"

export function ScoutCliDocsPage() {
  const [copied, setCopied] = useState(false)
  return (
    <div className="min-h-screen bg-bg text-text font-mono flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-xl rounded-[4px] border border-border bg-surface p-6 sm:p-8 space-y-6">
        <Link
          to="/scout"
          className="inline-flex items-center gap-1.5 text-xs text-text-faint hover:text-accent transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Scout Dashboard
        </Link>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-[4px] border border-accent/30 bg-accent/10 px-2.5 py-1 text-[10.5px] font-semibold text-accent uppercase tracking-wider">
            <Terminal className="h-3.5 w-3.5" />
            Phase 2 Preview · Coming Next
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            Helix Scout CLI
          </h1>
          <p className="text-xs text-text-muted leading-relaxed font-sans sm:text-sm">
            The standalone high-velocity command-line tool for scraping social leads, enriching contact databases, and exporting direct to CRM pipelines.
          </p>
        </div>

        {/* Terminal code snippet preview */}
        <div className="rounded-[4px] border border-border bg-surface-2 overflow-hidden text-xs">
          <div className="flex items-center justify-between border-b border-border/80 bg-surface px-3 py-1.5 font-mono text-[11px] text-text-muted">
            <span className="text-text-faint uppercase tracking-wider">bash</span>
            <button
              onClick={() => {
                const text = "curl -sSL https://helix.intelligence/install-scout.sh | bash\nhelix-scout --platform=github,linktree --input=handles.txt --enrich"
                navigator.clipboard?.writeText(text)
                setCopied(true)
                setTimeout(() => setCopied(false), 2000)
              }}
              type="button"
              aria-label="Copy CLI commands"
              className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-border/60 bg-surface-2/60 hover:bg-surface-2 hover:border-accent/40 text-[11px] text-text-muted hover:text-accent transition-all cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-accent" />
                  <span className="text-accent font-medium">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <div className="p-4 space-y-2">
            <div className="text-text-faint"># Installation preview (Phase 2)</div>
            <div className="text-accent">$ curl -sSL https://helix.intelligence/install-scout.sh | bash</div>
            <div className="text-text-muted mt-2"># Run headless lead extraction</div>
            <div className="text-white">$ helix-scout --platform=github,linktree --input=handles.txt --enrich</div>
          </div>
        </div>

        <div className="border-t border-border pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs text-text-faint">
          <span>In-app social lead gen is active now on /scout</span>
          <Button
            as={Link}
            to="/scout"
            variant="primary"
            size="sm"
            className="rounded-[4px] font-mono uppercase text-xs"
          >
            Launch Scout In-App →
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ScoutCliDocsPage
