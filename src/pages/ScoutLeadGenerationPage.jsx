import React, { useState, useEffect, useCallback } from "react"
import { Play, RotateCcw, AlertTriangle, Zap } from "lucide-react"
import { ScoutLeadGenSubNav } from "@/features/scout-leadgen/ScoutLeadGenSubNav"
import { SettingsStrip } from "@/features/scout-leadgen/SettingsStrip"
import { BriefForm } from "@/features/scout-leadgen/BriefForm"
import { SeedInput } from "@/features/scout-leadgen/SeedInput"
import { EnginePicker } from "@/features/scout-leadgen/EnginePicker"
import { RecipeLibrary } from "@/features/scout-leadgen/RecipeLibrary"
import { JobProgress } from "@/features/scout-leadgen/JobProgress"
import { LeadsTable } from "@/features/scout-leadgen/LeadsTable"
import { LeadDetail } from "@/features/scout-leadgen/LeadDetail"
import { ExportBar } from "@/features/scout-leadgen/ExportBar"
import { IdleState, NoLeadsState, WorkerOfflineState } from "@/features/scout-leadgen/EmptyStates"
import { useLeadGenJob, LEADGEN_PHASE } from "@/hooks/useLeadGenJob"
import { useAuth } from "@/context/AuthContext"

/**
 * Scout · Lead Generation composition root (scrapling_engine).
 * Page -> useLeadGenJob -> @/services. Social/Atlas lives at /scout/social and
 * is untouched by this surface.
 */
const DEFAULT_BRIEF = {
  icp: "KSA construction main contractors",
  geos: ["SA", "AE", "JO", "EG"],
  languages: ["ar", "en"],
  exclude_domains: [],
  max_pages: 80,
  max_leads: 50,
  credit_budget: 50,
  outreach_min_score: 50,
  enrich_emails: true,
  generate_outreach: true,
}

const DEFAULT_SEEDS = { urls: [], sitemap_url: null, shopify_url: null, domains_csv: null }

export function ScoutLeadGenerationPage() {
  const { user } = useAuth()
  const {
    phase, job, leads, selectedLead, health, recipes, error, isBusy,
    createJob, pause, resume, refresh, exportCsv, exportJsonl, selectLead, reset,
    fetchHealth, fetchRecipes,
  } = useLeadGenJob()

  const [brief, setBrief] = useState(DEFAULT_BRIEF)
  const [seeds, setSeeds] = useState(DEFAULT_SEEDS)
  const [engine, setEngine] = useState("stealth")
  const [mode, setMode] = useState("crawl")
  const [robotsObey, setRobotsObey] = useState(true)
  const [adaptive, setAdaptive] = useState(true)
  const [recipeId, setRecipeId] = useState(null)

  useEffect(() => {
    fetchHealth()
    fetchRecipes()
    const t = setInterval(fetchHealth, 30000)
    return () => clearInterval(t)
  }, [fetchHealth, fetchRecipes])

  const adoptRecipe = useCallback((recipe) => {
    if (!recipe) return
    if (recipe.engine_default) setEngine(recipe.engine_default)
    if (recipe.mode) setMode(recipe.mode)
    if (recipe.max_pages) setBrief((b) => ({ ...b, max_pages: recipe.max_pages }))
    if (typeof recipe.adaptive === "boolean") setAdaptive(recipe.adaptive)
    if (typeof recipe.robots_obey === "boolean") setRobotsObey(recipe.robots_obey)
  }, [])

  const workerOnline = health?.worker === "online"
  const offline = phase === LEADGEN_PHASE.WORKER_OFFLINE || (!workerOnline && !isBusy && !job)
  const running = phase === LEADGEN_PHASE.POLLING || phase === LEADGEN_PHASE.ENQUEUEING

  const handleRun = () => {
    createJob({
      brief: { ...brief, credit_budget: Number(brief.credit_budget) || 0 },
      seeds,
      engine_default: engine,
      mode,
      recipe_id: recipeId,
      robots_obey: robotsObey,
      adaptive,
      capture_xhr_pattern: null,
      enrich_emails: brief.enrich_emails,
      generate_outreach: brief.generate_outreach,
      proxy_mode: "off",
    })
  }

  return (
    <div className="min-h-full bg-bg">
      <ScoutLeadGenSubNav
        right={
          <span className="text-[11px] font-mono text-text-muted">
            engine <span className="text-accent font-bold">scrapling_engine</span>
            {user?.credit_balance !== undefined && (
              <>
                <span className="text-text-faint"> | </span>
                <Zap className="inline h-3 w-3 text-accent" />{" "}
                <span className="text-white font-bold">{Number(user.credit_balance).toFixed(1)}</span> credits
              </>
            )}
          </span>
        }
      />

      <div className="mx-auto w-full max-w-7xl space-y-4 p-4 sm:p-6">
        <SettingsStrip health={health} />

        {/* Error banner (worker offline / validation / job failure) */}
        {error && (
          <div className="flex items-start gap-2 rounded-[4px] border border-danger/40 bg-danger/5 px-3 py-2 font-mono text-[11px] text-danger">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {phase === LEADGEN_PHASE.WORKER_OFFLINE && <WorkerOfflineState onRefresh={fetchHealth} />}

        {/* Wizard: brief + seeds + engine + recipes (hidden while a job runs) */}
        {!running && phase !== LEADGEN_PHASE.READY && phase !== LEADGEN_PHASE.FAILED && (
          <div className="space-y-4 rounded-[4px] border border-border bg-surface/40 p-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="space-y-2">
                <h3 className="text-[11px] uppercase tracking-widest text-text-faint font-semibold">
                  1 · ICP brief
                </h3>
                <BriefForm value={brief} onChange={setBrief} disabled={isBusy} />
              </div>
              <div className="space-y-2">
                <h3 className="text-[11px] uppercase tracking-widest text-text-faint font-semibold">
                  2 · seeds
                </h3>
                <SeedInput value={seeds} onChange={setSeeds} disabled={isBusy} />
                <h3 className="pt-1 text-[11px] uppercase tracking-widest text-text-faint font-semibold">
                  3 · engine & mode
                </h3>
                <EnginePicker
                  value={engine} onChange={setEngine}
                  mode={mode} onModeChange={setMode}
                  robotsObey={robotsObey} onRobotsChange={setRobotsObey}
                  adaptive={adaptive} onAdaptiveChange={setAdaptive}
                  disabled={isBusy}
                />
              </div>
            </div>

            <RecipeLibrary
              recipes={recipes}
              selectedId={recipeId}
              onSelect={setRecipeId}
              onAdopt={adoptRecipe}
              disabled={isBusy}
            />

            <div className="flex flex-wrap items-center gap-3 border-t border-border/60 pt-3">
              <button
                type="button"
                onClick={handleRun}
                disabled={isBusy || !workerOnline}
                title={!workerOnline ? "Worker offline - start the Scrapling worker" : "Queue the job"}
                className="flex items-center gap-2 rounded-[4px] bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black hover:bg-[#e4ff75] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Play className="h-3.5 w-3.5" />
                {isBusy ? "queueing…" : "run lead generation"}
              </button>
              <span className="font-mono text-[11px] text-text-muted">
                est. cost ≈ {(
                  Number(brief.credit_budget) || 0
                ) > 0 ? "charged at enqueue" : "—"} · charged per job, refunds on dead jobs
              </span>
            </div>
          </div>
        )}

        {/* Job transcript (real worker output) */}
        {job && (
          <JobProgress
            job={job}
            leadsCount={leads.length}
            onPause={pause}
            onResume={resume}
            onRefresh={refresh}
          />
        )}

        {/* Export + results */}
        {job && <ExportBar job={job} leadsCount={leads.length} onExportCsv={exportCsv} onExportJsonl={exportJsonl} />}

        {leads.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
            <div className="lg:col-span-7">
              <LeadsTable leads={leads} selectedLead={selectedLead} onSelectLead={selectLead} />
            </div>
            <div className="lg:col-span-5">
              <LeadDetail lead={selectedLead} />
            </div>
          </div>
        ) : (
          job && !running && <NoLeadsState job={job} />
        )}

        {!job && phase === LEADGEN_PHASE.IDLE && workerOnline && (
          <IdleState onRunHint="robots.txt honored by default · public pages only · outreach drafted, never sent" />
        )}

        {(phase === LEADGEN_PHASE.READY || phase === LEADGEN_PHASE.FAILED) && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={reset}
              className="flex items-center gap-1.5 rounded border border-border bg-surface px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-white hover:border-accent/50"
            >
              <RotateCcw className="h-3.5 w-3.5" /> new job
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ScoutLeadGenerationPage
