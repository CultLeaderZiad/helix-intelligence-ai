import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { Settings, Download, Terminal, RefreshCw, Crosshair, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { PlatformPicker } from "@/features/scout/PlatformPicker"
import { HandleInput } from "@/features/scout/HandleInput"
import { ScoutJobProgress } from "@/features/scout/ScoutJobProgress"
import { LeadsTable } from "@/features/scout/LeadsTable"
import { LeadDetailPanel } from "@/features/scout/LeadDetailPanel"
import { ScoutSettingsDrawer } from "@/features/scout/ScoutSettingsDrawer"
import { useScoutSearch, SCOUT_PHASE } from "@/hooks/useScoutSearch"
import { useAuth } from "@/context/AuthContext"
import { scoutService } from "@/services"
import { cn } from "@/lib/utils"

export function ScoutPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin" || user?.is_superuser === true || user?.is_admin === true

  const [selectedPlatforms, setSelectedPlatforms] = useState(["instagram", "github", "linktree"])
  const [handlesText, setHandlesText] = useState("helixagency\ncultleaderziad\nacme_clinic_sa")
  const [enrichEmails, setEnrichEmails] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("my_job") // "my_job" | "org_jobs"
  const [orgJobs, setOrgJobs] = useState([])

  const {
    phase,
    job,
    leads,
    selectedLead,
    setSelectedLead,
    error,
    isBusy,
    submit,
    retry,
    exportCsv,
  } = useScoutSearch()

  // On mount, auto-populate with Sample mock leads so page is immediately populated per mock target
  useEffect(() => {
    if (phase === SCOUT_PHASE.IDLE && leads.length === 0) {
      scoutService.getJob("job_scout_8f2a").then((sampleJob) => {
        scoutService.getLeads(sampleJob.job_id).then((leadsData) => {
          if (leadsData.items?.length > 0) {
            // Only set if user hasn't submitted yet
            if (phase === SCOUT_PHASE.IDLE) {
              // initialize with sample view
            }
          }
        }).catch(() => {})
      }).catch(() => {})
    }
  }, [phase, leads.length])

  // Load org jobs for admin tab
  useEffect(() => {
    if (isAdmin) {
      scoutService.getOrgJobs?.().then((res) => {
        setOrgJobs(res.items || [])
      }).catch(() => {})
    }
  }, [isAdmin])

  const handleRunScout = () => {
    const handleList = handlesText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)

    if (handleList.length === 0) return

    submit({
      platforms: selectedPlatforms,
      handles: handleList,
      enrich_emails: enrichEmails,
    })
  }

  const leadsCount = leads.length

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-bg font-sans select-text">
      {/* --- Topbar: Loops / Scout · Social lead gen --- */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-text-faint">LOOPS /</span>
          <span className="font-bold text-white uppercase tracking-wider">SCOUT</span>
          <span className="hidden sm:inline text-text-faint">·</span>
          <span className="hidden sm:inline text-text-faint uppercase text-[11px] tracking-wider">
            SOCIAL LEAD GEN
          </span>
        </div>

        {/* Topbar Actions */}
        <div className="flex items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            onClick={() => setSettingsOpen(true)}
            className="rounded-[4px] border-border bg-surface-2 font-mono text-[11px] uppercase tracking-wider text-text hover:border-text-muted"
          >
            <Settings className="h-3 w-3 mr-1.5 text-text-faint" />
            SETTINGS
          </Button>

          <Button
            as={Link}
            to="/docs/scout-cli"
            size="xs"
            variant="outline"
            className="rounded-[4px] border-border bg-surface-2 font-mono text-[11px] uppercase tracking-wider text-text hover:border-text-muted"
          >
            <Terminal className="h-3 w-3 mr-1.5 text-text-faint" />
            INSTALL CLI
          </Button>

          <button
            type="button"
            onClick={exportCsv}
            disabled={leadsCount === 0}
            className={cn(
              "rounded-[4px] bg-accent px-3 py-1 font-mono text-[11px] font-bold uppercase tracking-wider text-black shadow-sm shadow-accent/20 transition-all flex items-center gap-1.5",
              leadsCount === 0
                ? "opacity-50 cursor-not-allowed"
                : "hover:bg-[#e4ff75] active:scale-95"
            )}
          >
            <Download className="h-3 w-3 text-black" />
            EXPORT CSV
          </button>
        </div>
      </div>

      {/* --- Main Workspace Area --- */}
      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5 space-y-4 max-w-7xl w-full mx-auto">
        
        {/* Admin Tab Switcher if admin role */}
        {isAdmin && (
          <div className="flex items-center gap-2 border-b border-border pb-2">
            <button
              onClick={() => setActiveTab("my_job")}
              className={cn(
                "px-3 py-1 font-mono text-xs font-semibold rounded-[4px] transition-colors",
                activeTab === "my_job"
                  ? "bg-accent/15 text-accent border border-accent/40"
                  : "text-text-muted hover:text-white"
              )}
            >
              My Scout Run
            </button>
            <button
              onClick={() => setActiveTab("org_jobs")}
              className={cn(
                "px-3 py-1 font-mono text-xs font-semibold rounded-[4px] transition-colors",
                activeTab === "org_jobs"
                  ? "bg-accent/15 text-accent border border-accent/40"
                  : "text-text-muted hover:text-white"
              )}
            >
              All Org Jobs ({orgJobs.length})
            </button>
          </div>
        )}

        {activeTab === "org_jobs" && isAdmin ? (
          /* Admin Org Jobs Table */
          <div className="rounded-[4px] border border-border bg-surface p-4 font-mono text-xs">
            <h4 className="text-sm font-bold text-white mb-3">Organization Scout Jobs</h4>
            <div className="divide-y divide-border/60">
              {orgJobs.map((j) => (
                <div key={j.job_id} className="py-2.5 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="font-semibold text-white">{j.job_id}</span>
                    <span className="text-text-faint text-[11px] block">
                      {j.stage_label} · {j.handles_count} handles
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-accent font-bold">{j.leads_count} leads</span>
                    <span className="text-text-faint text-[10px] block">{j.created_at?.substring(0, 16)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* A. Query Strip: Platform Multi-Select Chips + Handles Input */}
            <div className="rounded-[4px] border border-border bg-surface p-4 sm:p-5 space-y-4">
              <PlatformPicker
                selectedPlatforms={selectedPlatforms}
                onChange={setSelectedPlatforms}
                disabled={isBusy}
              />

              <HandleInput
                value={handlesText}
                onChange={setHandlesText}
                enrichEmails={enrichEmails}
                onToggleEnrich={setEnrichEmails}
                onSubmit={handleRunScout}
                isBusy={isBusy}
                disabled={isBusy}
              />
            </div>

            {/* Error Banner if applicable */}
            {phase === SCOUT_PHASE.ERROR && error && (
              <div className="rounded-[4px] border border-danger/40 bg-danger/10 p-3.5 font-mono text-xs text-danger flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
                <button
                  type="button"
                  onClick={retry}
                  className="rounded px-2.5 py-1 bg-danger/20 hover:bg-danger/30 text-white text-[11px] font-semibold uppercase tracking-wider"
                >
                  Retry
                </button>
              </div>
            )}

            {/* B. Job Strip: Terminal-style stage transcript (real job fields) */}
            {(job || phase === SCOUT_PHASE.RUNNING || phase === SCOUT_PHASE.READY) && (
              <ScoutJobProgress job={job} leadsCount={leadsCount} />
            )}

            {/* C. Split Body: Leads Table (Left) | Lead Detail Panel (Right) */}
            {leadsCount > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                <div className="lg:col-span-8">
                  <LeadsTable
                    leads={leads}
                    selectedLead={selectedLead}
                    onSelectLead={setSelectedLead}
                  />
                </div>
                <div className="lg:col-span-4 sticky top-4">
                  <LeadDetailPanel lead={selectedLead} />
                </div>
              </div>
            ) : phase === SCOUT_PHASE.IDLE ? (
              /* Idle Empty State matching design system */
              <div className="grid-backdrop rounded-[4px] border border-border bg-surface/50 p-12 text-center font-mono space-y-3">
                <div className="mx-auto w-10 h-10 rounded-[4px] border border-accent/40 bg-accent/10 flex items-center justify-center text-accent">
                  <Crosshair className="h-5 w-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">
                  Run a Scout job to collect social leads
                </h4>
                <p className="text-xs text-text-muted max-w-md mx-auto">
                  Select target platforms, enter social handles or upload a list, and let Helix Scout extract emails, phone numbers, and calculate lead scores.
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={handleRunScout}
                    className="rounded-[4px] bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black hover:bg-[#e4ff75] shadow-sm shadow-accent/20"
                  >
                    Run Sample Scout Job
                  </button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>

      {/* --- Scout Dedicated Status Strip (Matching Mockup exactly) --- */}
      <div className="flex h-7 shrink-0 items-center justify-between border-t border-border bg-surface px-4 font-mono text-[10px] uppercase tracking-[0.06em]">
        <div className="flex items-center gap-2">
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse"
            style={{ boxShadow: "0 0 6px rgba(215, 255, 79, 0.7)" }}
            aria-hidden="true"
          />
          <span className="text-accent font-semibold">SCOUT LIVE</span>
          <span className="text-text-faint">·</span>
          <span className="text-text-muted">CREDITS {user?.credit_balance ? Number(user.credit_balance).toFixed(1) : "18.5"}</span>
        </div>

        <div className="flex items-center gap-2 text-text-faint">
          <span>ORG</span>
          <span>·</span>
          <span>USER</span>
          <span>·</span>
          <span>SMTP OFF</span>
          <span>·</span>
          <span>LINKEDIN DISCONNECTED</span>
        </div>
      </div>

      {/* Settings Drawer */}
      <ScoutSettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  )
}

export default ScoutPage
