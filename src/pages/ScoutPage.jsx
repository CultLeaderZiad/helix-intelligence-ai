import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { Settings, Download, Terminal, RefreshCw, Crosshair, AlertCircle, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { PlatformPicker } from "@/features/scout/PlatformPicker"
import { HandleInput } from "@/features/scout/HandleInput"
import { ScoutJobProgress } from "@/features/scout/ScoutJobProgress"
import { LeadsTable } from "@/features/scout/LeadsTable"
import { LeadDetailPanel } from "@/features/scout/LeadDetailPanel"
import { ScoutSettingsDrawer } from "@/features/scout/ScoutSettingsDrawer"
import { ScoutModeTabs } from "@/features/scout/ScoutModeTabs"
import { MapsQueryForm } from "@/features/scout/MapsQueryForm"
import { MapsLeadsTable } from "@/features/scout/MapsLeadsTable"
import { MapsLeadDetailPanel } from "@/features/scout/MapsLeadDetailPanel"
import { useScoutSearch, SCOUT_PHASE } from "@/hooks/useScoutSearch"
import { useMapsScoutSearch, MAPS_SCOUT_PHASE } from "@/hooks/useMapsScoutSearch"
import { useAuth } from "@/context/AuthContext"
import { scoutService, mapsScoutService } from "@/services"
import { cn } from "@/lib/utils"

export function ScoutPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin" || user?.is_superuser === true || user?.is_admin === true

  // Mode: "social" | "maps"
  const [mode, setMode] = useState("social")

  // Social Mode State
  const [selectedPlatforms, setSelectedPlatforms] = useState(["instagram", "github", "linktree"])
  const [handlesText, setHandlesText] = useState("cultleaderziad\nhttps://github.com/cultleaderziad")
  const [enrichEmails, setEnrichEmails] = useState(true)

  // Maps Mode State
  const [mapsKeyword, setMapsKeyword] = useState("Dentists")
  const [mapsCity, setMapsCity] = useState("Riyadh, SA")
  const [mapsDepth, setMapsDepth] = useState(5)
  const [mapsExtractEmails, setMapsExtractEmails] = useState(true)
  const [mapsPullSocials, setMapsPullSocials] = useState(false)

  // Global Settings & Org State
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsData, setSettingsData] = useState(null)
  const [adminTab, setAdminTab] = useState("current") // "current" | "org_social" | "org_maps"
  const [orgSocialJobs, setOrgSocialJobs] = useState([])
  const [orgMapsJobs, setOrgMapsJobs] = useState([])

  // Social Hook
  const {
    phase: socialPhase,
    job: socialJob,
    leads: socialLeads,
    selectedLead: selectedSocialLead,
    setSelectedLead: setSelectedSocialLead,
    error: socialError,
    isBusy: isSocialBusy,
    submit: submitSocial,
    retry: retrySocial,
    exportCsv: exportSocialCsv,
  } = useScoutSearch()

  // Maps Hook
  const {
    phase: mapsPhase,
    job: mapsJob,
    leads: mapsLeads,
    selectedLead: selectedMapsLead,
    setSelectedLead: setSelectedMapsLead,
    error: mapsError,
    isBusy: isMapsBusy,
    submit: submitMaps,
    retry: retryMaps,
    exportCsv: exportMapsCsv,
  } = useMapsScoutSearch()

  // Fetch settings on mount
  useEffect(() => {
    scoutService.getSettings?.().then((res) => {
      setSettingsData(res)
    }).catch(() => {})
  }, [settingsOpen])

  // Load org jobs for admin tab
  useEffect(() => {
    if (isAdmin) {
      scoutService.getOrgJobs?.().then((res) => {
        setOrgSocialJobs(res.items || [])
      }).catch(() => {})

      mapsScoutService.getOrgJobs?.().then((res) => {
        setOrgMapsJobs(res.items || [])
      }).catch(() => {})
    }
  }, [isAdmin])

  // Handlers
  const handleRunSocialScout = () => {
    const handleList = handlesText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)

    if (handleList.length === 0) return

    submitSocial({
      platforms: selectedPlatforms,
      handles: handleList,
      enrich_emails: enrichEmails,
    })
  }

  const handleRunMapsScout = () => {
    if (!mapsKeyword.trim() || !mapsCity.trim()) return

    submitMaps({
      keyword: mapsKeyword.trim(),
      city: mapsCity.trim(),
      depth: mapsDepth,
      extract_emails: mapsExtractEmails,
      pull_socials: mapsPullSocials,
    })
  }

  // Queue discovered business socials from Maps mode into Social mode
  const handleQueueSocialsFromMaps = (socialUrls = []) => {
    if (!socialUrls || socialUrls.length === 0) return
    const currentHandles = handlesText.split("\n").filter(Boolean)
    const combined = Array.from(new Set([...currentHandles, ...socialUrls])).slice(0, 25)
    setHandlesText(combined.join("\n"))
    setMode("social")
  }

  const currentLeadsCount = mode === "social" ? socialLeads.length : mapsLeads.length
  const handleExport = mode === "social" ? exportSocialCsv : exportMapsCsv

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-bg font-sans select-text">
      {/* Topbar: Loops / Scout · Lead Gen */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-text-faint">LOOPS /</span>
          <span className="font-bold text-white uppercase tracking-wider">SCOUT</span>
          <span className="hidden sm:inline text-text-faint">·</span>
          <span className="hidden sm:inline text-accent uppercase text-[11px] font-bold tracking-wider">
            LEAD GEN
          </span>
        </div>

        {/* Topbar Actions */}
        <div className="flex items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            onClick={() => setSettingsOpen(true)}
            className="border-border text-text-muted hover:text-white"
          >
            <Settings className="h-3.5 w-3.5 mr-1" />
            SETTINGS
          </Button>

          <Link to="/docs/scout-cli">
            <Button
              size="xs"
              variant="outline"
              className="border-border text-text-muted hover:text-accent"
            >
              <Terminal className="h-3.5 w-3.5 mr-1" />
              INSTALL CLI
            </Button>
          </Link>

          <button
            type="button"
            onClick={handleExport}
            disabled={currentLeadsCount === 0}
            className={cn(
              "rounded-[4px] bg-accent px-3 py-1 font-mono text-[11px] font-bold uppercase tracking-wider text-black shadow-sm shadow-accent/20 transition-all flex items-center gap-1.5",
              currentLeadsCount === 0
                ? "opacity-50 cursor-not-allowed"
                : "hover:bg-[#e4ff75] active:scale-95"
            )}
          >
            <Download className="h-3 w-3 text-black" />
            EXPORT CSV
          </button>
        </div>
      </div>

      {/* Scout Dual Mode Tabs & Live Status Strip */}
      <ScoutModeTabs
        mode={mode}
        onSelectMode={setMode}
        settings={settingsData}
        credits={user?.credit_balance ?? 25.0}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5 space-y-4 max-w-7xl w-full mx-auto">
        {/* Admin Multi-Tenant View Switcher */}
        {isAdmin && (
          <div className="flex items-center gap-2 border-b border-border pb-2 font-mono text-xs">
            <button
              onClick={() => setAdminTab("current")}
              className={cn(
                "px-3 py-1 rounded-[4px] font-semibold transition-colors",
                adminTab === "current"
                  ? "bg-accent/15 text-accent border border-accent/40"
                  : "text-text-muted hover:text-white"
              )}
            >
              Active Workspace
            </button>
            <button
              onClick={() => setAdminTab("org_social")}
              className={cn(
                "px-3 py-1 rounded-[4px] font-semibold transition-colors",
                adminTab === "org_social"
                  ? "bg-accent/15 text-accent border border-accent/40"
                  : "text-text-muted hover:text-white"
              )}
            >
              Org Social Jobs ({orgSocialJobs.length})
            </button>
            <button
              onClick={() => setAdminTab("org_maps")}
              className={cn(
                "px-3 py-1 rounded-[4px] font-semibold transition-colors",
                adminTab === "org_maps"
                  ? "bg-accent/15 text-accent border border-accent/40"
                  : "text-text-muted hover:text-white"
              )}
            >
              Org Maps Jobs ({orgMapsJobs.length})
            </button>
          </div>
        )}

        {/* ============================================================ */}
        {/* ADMIN TAB: ORG SOCIAL JOBS */}
        {/* ============================================================ */}
        {isAdmin && adminTab === "org_social" ? (
          <div className="rounded-[4px] border border-border bg-surface p-4 font-mono text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2 text-[11px] text-text-muted font-semibold uppercase tracking-wider">
              <span>Organization Social Scout Jobs</span>
              <span className="text-accent">{orgSocialJobs.length} records</span>
            </div>
            <div className="divide-y divide-border/40">
              {orgSocialJobs.map((j) => (
                <div key={j.job_id} className="py-2.5 flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold block">{j.job_id}</span>
                    <span className="text-text-muted text-[11px]">{j.handles_count} targets · {j.status}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-accent font-bold">{j.leads_count} verified leads</span>
                    <span className="text-text-faint text-[10px] block">{j.created_at?.substring(0, 16)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : isAdmin && adminTab === "org_maps" ? (
          /* ============================================================ */
          /* ADMIN TAB: ORG MAPS JOBS */
          /* ============================================================ */
          <div className="rounded-[4px] border border-border bg-surface p-4 font-mono text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2 text-[11px] text-text-muted font-semibold uppercase tracking-wider">
              <span>Organization Google Maps Scout Jobs</span>
              <span className="text-accent">{orgMapsJobs.length} records</span>
            </div>
            <div className="divide-y divide-border/40">
              {orgMapsJobs.map((j) => (
                <div key={j.job_id} className="py-2.5 flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold block">{j.keyword} ({j.city})</span>
                    <span className="text-text-muted text-[11px]">{j.job_id} · {j.status}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-accent font-bold">{j.results_count} leads</span>
                    <span className="text-text-faint text-[10px] block">{j.created_at?.substring(0, 16)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : mode === "social" ? (
          /* ============================================================ */
          /* MODE A: SOCIAL PROFILES */
          /* ============================================================ */
          <>
            <div className="rounded-[4px] border border-border bg-surface p-4 sm:p-5 space-y-4">
              <PlatformPicker
                selectedPlatforms={selectedPlatforms}
                onChange={setSelectedPlatforms}
                disabled={isSocialBusy}
              />

              <HandleInput
                value={handlesText}
                onChange={setHandlesText}
                enrichEmails={enrichEmails}
                onToggleEnrich={setEnrichEmails}
                onSubmit={handleRunSocialScout}
                isBusy={isSocialBusy}
                disabled={isSocialBusy}
              />
            </div>

            {/* Error Banner */}
            {socialPhase === SCOUT_PHASE.ERROR && socialError && (
              <div className="rounded-[4px] border border-danger/40 bg-danger/10 p-3.5 font-mono text-xs text-danger flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{socialError}</span>
                </div>
                <button
                  type="button"
                  onClick={retrySocial}
                  className="rounded px-2.5 py-1 bg-danger/20 hover:bg-danger/30 text-white text-[11px] font-semibold uppercase tracking-wider"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Terminal Transcript Strip */}
            {(socialJob || socialPhase === SCOUT_PHASE.RUNNING || socialPhase === SCOUT_PHASE.READY) && (
              <ScoutJobProgress job={socialJob} leadsCount={socialLeads.length} />
            )}

            {/* Results Split Body */}
            {socialLeads.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                <div className="lg:col-span-8">
                  <LeadsTable
                    leads={socialLeads}
                    selectedLead={selectedSocialLead}
                    onSelectLead={setSelectedSocialLead}
                  />
                </div>
                <div className="lg:col-span-4 sticky top-4">
                  <LeadDetailPanel lead={selectedSocialLead} />
                </div>
              </div>
            ) : socialPhase === SCOUT_PHASE.IDLE ? (
              <div className="rounded-[4px] border border-border bg-surface/50 p-10 text-center font-mono space-y-3">
                <div className="mx-auto w-10 h-10 rounded-[4px] border border-accent/40 bg-accent/10 flex items-center justify-center text-accent">
                  <Crosshair className="h-5 w-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">
                  Social Lead Generation Pipeline
                </h4>
                <p className="text-xs text-text-muted max-w-md mx-auto">
                  Enter social handles or full profile URLs above (IG, LinkedIn, GitHub, Linktree, TikTok, YouTube). Scrapers verify real public profiles, extract published contact points, and calculate lead scores.
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isSocialBusy || handlesText.trim().length === 0}
                    onClick={handleRunSocialScout}
                    className="rounded-[4px] bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black hover:bg-[#e4ff75] shadow-sm shadow-accent/20"
                  >
                    RUN SCOUT
                  </button>
                </div>
              </div>
            ) : null}
          </>
        ) : (
          /* ============================================================ */
          /* MODE B: MAPS LEADS */
          /* ============================================================ */
          <>
            <MapsQueryForm
              keyword={mapsKeyword}
              setKeyword={setMapsKeyword}
              city={mapsCity}
              setCity={setMapsCity}
              depth={mapsDepth}
              setDepth={setMapsDepth}
              extractEmails={mapsExtractEmails}
              setExtractEmails={setMapsExtractEmails}
              pullSocials={mapsPullSocials}
              setPullSocials={setMapsPullSocials}
              onSubmit={handleRunMapsScout}
              isBusy={isMapsBusy}
            />

            {/* Maps Error Banner */}
            {mapsPhase === MAPS_SCOUT_PHASE.ERROR && mapsError && (
              <div className="rounded-[4px] border border-danger/40 bg-danger/10 p-3.5 font-mono text-xs text-danger flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{mapsError}</span>
                </div>
                <button
                  type="button"
                  onClick={retryMaps}
                  className="rounded px-2.5 py-1 bg-danger/20 hover:bg-danger/30 text-white text-[11px] font-semibold uppercase tracking-wider"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Maps Job Transcript Strip */}
            {(mapsJob || mapsPhase === MAPS_SCOUT_PHASE.RUNNING || mapsPhase === MAPS_SCOUT_PHASE.READY) && (
              <ScoutJobProgress job={mapsJob} leadsCount={mapsLeads.length} />
            )}

            {/* Maps Results Split Body */}
            {mapsLeads.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                <div className="lg:col-span-8">
                  <MapsLeadsTable
                    leads={mapsLeads}
                    selectedLead={selectedMapsLead}
                    onSelectLead={setSelectedMapsLead}
                  />
                </div>
                <div className="lg:col-span-4 sticky top-4">
                  <MapsLeadDetailPanel
                    lead={selectedMapsLead}
                    onQueueSocials={handleQueueSocialsFromMaps}
                  />
                </div>
              </div>
            ) : mapsPhase === MAPS_SCOUT_PHASE.IDLE ? (
              <div className="rounded-[4px] border border-border bg-surface/50 p-10 text-center font-mono space-y-3">
                <div className="mx-auto w-10 h-10 rounded-[4px] border border-accent/40 bg-accent/10 flex items-center justify-center text-accent">
                  <Crosshair className="h-5 w-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">
                  Google Maps Business Lead Generation
                </h4>
                <p className="text-xs text-text-muted max-w-md mx-auto">
                  Search any niche in any city (e.g. Dentists in Riyadh, Specialty Coffee in Austin). Extracts business name, phone, address, website, rating, verified emails, and public social links.
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isMapsBusy || !mapsKeyword.trim() || !mapsCity.trim()}
                    onClick={handleRunMapsScout}
                    className="rounded-[4px] bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black hover:bg-[#e4ff75] shadow-sm shadow-accent/20"
                  >
                    RUN MAPS SCOUT
                  </button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>

      {/* Scout Settings Drawer */}
      <ScoutSettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  )
}

export default ScoutPage
