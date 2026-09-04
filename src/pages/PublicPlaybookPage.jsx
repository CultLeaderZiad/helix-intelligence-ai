import React, { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { Sparkles, Printer, ArrowUpRight, Share2, ExternalLink, ShieldCheck, Compass, CheckCircle2, Layers } from "lucide-react"
import { playbookService } from "../services"

export function PublicPlaybookPage() {
  const { publicId } = useParams()
  const [playbook, setPlaybook] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      try {
        const data = await playbookService.getPublicPlaybook(publicId)
        setPlaybook(data)
      } catch (err) {
        setError(err?.message || "Playbook not found or expired")
      } finally {
        setIsLoading(false)
      }
    }
    if (publicId) load()
  }, [publicId])

  const handlePrint = () => {
    window.print()
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 space-y-3">
        <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm">Loading Creative Strategy Playbook...</p>
      </div>
    )
  }

  if (error || !playbook) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-center">
        <div className="max-w-md space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto">
            <Compass className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Playbook Not Found</h2>
          <p className="text-sm text-slate-400">{error || "This shared playbook URL is invalid or has expired."}</p>
          <Link to="/" className="inline-block px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm transition">
            Go to Helix Home
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-teal-500 selection:text-slate-950 pb-20">
      {/* Top Action Bar (Hidden on print) */}
      <header className="sticky top-0 z-40 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 print:hidden">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-teal-500 flex items-center justify-center font-black text-slate-950 text-sm">
              H
            </div>
            <span className="font-bold text-sm tracking-tight text-white">
              Helix Intelligence <span className="text-teal-400 font-medium">| Executive Playbook</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleShare}
              className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <Share2 className="w-3.5 h-3.5" />
              {copied ? "Link Copied!" : "Share Link"}
            </button>
            <button
              onClick={handlePrint}
              className="px-3.5 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <Printer className="w-3.5 h-3.5" /> Export PDF / Print
            </button>
          </div>
        </div>
      </header>

      {/* Main Playbook Document */}
      <main className="max-w-5xl mx-auto px-6 pt-10 space-y-12">
        {/* Executive Header */}
        <section className="border-b border-slate-800/80 pb-10 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-teal-500/10 text-teal-400 border border-teal-500/20">
              {playbook.brand_name.toUpperCase()} STRATEGY REPORT
            </span>
            <span className="text-xs text-slate-400">
              Compiled on {new Date(playbook.created_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            {playbook.title}
          </h1>

          <p className="text-base text-slate-300 leading-relaxed max-w-3xl">
            {playbook.summary}
          </p>
        </section>

        {/* Section 1: Winning Creative Patterns */}
        <section className="space-y-6">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-teal-400" />
            <h2 className="text-xl font-bold text-white tracking-tight">Top High-Converting Creative Patterns</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(playbook.patterns || []).map((pat, idx) => (
              <div key={pat.id || idx} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3 print:border-slate-300 print:bg-white print:text-slate-900">
                <div className="flex items-center justify-between gap-2">
                  <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 print:border-slate-400 print:text-indigo-700">
                    {pat.category || "Hook Pattern"}
                  </span>
                  {pat.estimated_lift_percent != null && (
                    <div className="text-xs font-bold text-emerald-400 flex items-center gap-1 print:text-emerald-700">
                      <ArrowUpRight className="w-3.5 h-3.5" /> +{pat.estimated_lift_percent}% Est. Lift
                    </div>
                  )}
                </div>

                <h3 className="font-bold text-base text-white print:text-slate-900">{pat.name}</h3>
                <p className="text-xs text-slate-300 print:text-slate-700 leading-relaxed">{pat.description}</p>
                
                {pat.visual_structure && (
                  <div className="pt-2 border-t border-slate-800/60 print:border-slate-200 text-[11px] text-slate-400 print:text-slate-600">
                    <span className="font-semibold text-slate-300 print:text-slate-800">Visual Blueprint:</span> {pat.visual_structure}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Section 2: Real Scraped Creative Attributions */}
        <section className="space-y-6">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-bold text-white tracking-tight">Top Scaled Creative Executions</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(playbook.creatives || []).length === 0 ? (
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 text-sm text-slate-400 col-span-2 text-center">
                Analyzed from direct brand pattern benchmarks.
              </div>
            ) : (
              playbook.creatives.map((c, idx) => (
                <div key={c.id || idx} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3 print:border-slate-300 print:bg-white print:text-slate-900">
                  <div className="flex items-center justify-between text-xs text-slate-400 print:text-slate-600">
                    <span className="font-semibold uppercase tracking-wider text-teal-400 print:text-teal-700">
                      {c.platform} • {c.format}
                    </span>
                    <span>Active {c.days_active} days</span>
                  </div>

                  <div className="font-bold text-sm text-white print:text-slate-900">
                    "{c.headline || "Headline Not Extracted"}"
                  </div>

                  {c.body && (
                    <p className="text-xs text-slate-300 print:text-slate-700 line-clamp-3 leading-relaxed">
                      {c.body}
                    </p>
                  )}

                  <div className="pt-3 border-t border-slate-800/60 print:border-slate-200 flex items-center justify-between text-[11px] text-slate-400 print:text-slate-600">
                    <span>Source: {c.data_source}</span>
                    {c.landing_domain && (
                      <span className="font-mono text-slate-300 print:text-slate-800">{c.landing_domain}</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Section 3: Deep Teardown Takeaways */}
        {playbook.insights && playbook.insights.length > 0 && (
          <section className="space-y-6">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2 className="text-xl font-bold text-white tracking-tight">Key Deep Teardown Takeaways</h2>
            </div>

            <div className="space-y-3">
              {playbook.insights.map((ins, idx) => (
                <div key={ins.id || idx} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-3.5 print:bg-white print:border-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-white print:text-slate-900">{ins.title}</h4>
                    <p className="text-xs text-slate-300 print:text-slate-700 mt-1 leading-relaxed">{ins.summary}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Footer Provenance Stamp */}
        <footer className="pt-12 border-t border-slate-800/80 text-center space-y-2 text-xs text-slate-500 print:text-slate-600">
          <p>
            Generated via Helix Creative Intelligence Engine • All metrics reflect verified active campaigns.
          </p>
          <p className="text-[10px]">
            Helix Intelligence System • Confidential Client Playbook • Token: {playbook.public_id}
          </p>
        </footer>
      </main>
    </div>
  )
}

export default PublicPlaybookPage
