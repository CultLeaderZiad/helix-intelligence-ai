import { useEffect, useState } from "react"
import { Users, ChevronDown, Loader, AlertCircle, ShieldAlert, HelpCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { simulationService } from "@/services"
import { useSimulation } from "@/hooks/useSimulation"

/**
 * "Rehearse this creative with synthetic audiences" — an LLM role-plays a
 * handful of preset personas reacting to the creative brief before any
 * money is spent. This is deliberately NOT a performance predictor: every
 * result is visibly tagged as simulated and never shown alongside real
 * CTR/conversion numbers.
 */
export function AudienceSimulationPanel({ creativeId }) {
  const [expanded, setExpanded] = useState(false)
  const [segments, setSegments] = useState([])
  const [selectedSegments, setSelectedSegments] = useState(new Set())
  const { phase, report, error, run, isBusy } = useSimulation()

  useEffect(() => {
    let cancelled = false
    simulationService.listSegments().then((list) => {
      if (cancelled) return
      setSegments(list)
      setSelectedSegments(new Set(list.slice(0, 3).map((s) => s.id)))
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  function toggleSegment(id) {
    setSelectedSegments((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleRun() {
    if (!creativeId || selectedSegments.size === 0 || isBusy) return
    run(creativeId, [...selectedSegments]).catch(() => {})
  }

  if (!creativeId) return null

  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-3.5 w-3.5 text-accent" />
          <span className="text-xs font-mono font-semibold text-text">
            Simulate with Synthetic Audiences
          </span>
        </div>
        <Button
          size="xs"
          variant="outline"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-[11px]"
        >
          {expanded ? "Hide" : "Rehearse This Creative"}
          <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
        </Button>
      </div>

      {expanded && (
        <div className="mt-3 flex flex-col gap-3 border-t border-border pt-3">
          <p className="text-[11px] text-text-muted leading-relaxed flex items-start gap-1.5">
            <HelpCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-text-faint" />
            An AI role-plays each selected persona reacting to this creative to catch
            objections, confusing claims, and compliance risk before you spend. This is a
            simulated rehearsal, not a prediction of real audience performance.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {segments.map((segment) => (
              <label
                key={segment.id}
                className={`flex items-start gap-2 rounded border p-2 text-left cursor-pointer transition-colors ${
                  selectedSegments.has(segment.id)
                    ? "border-accent bg-accent/5"
                    : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedSegments.has(segment.id)}
                  onChange={() => toggleSegment(segment.id)}
                  className="mt-0.5"
                />
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-text">{segment.label}</p>
                  <p className="text-[10px] text-text-muted leading-snug">{segment.description}</p>
                </div>
              </label>
            ))}
          </div>

          <Button
            size="sm"
            variant="primary"
            onClick={handleRun}
            disabled={isBusy || selectedSegments.size === 0}
            className="w-fit flex items-center gap-1.5 font-semibold"
          >
            {isBusy ? (
              <>
                <Loader className="h-3.5 w-3.5 animate-spin" /> Simulating Reactions...
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" /> Run Simulation ({selectedSegments.size} persona
                {selectedSegments.size === 1 ? "" : "s"})
              </>
            )}
          </Button>

          {phase === "error" && (
            <div className="flex items-center gap-2 text-[11px] text-destructive">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {typeof error === "string" ? error : "Simulation failed. Please try again."}
            </div>
          )}

          {report && <SimulationReportView report={report} />}
        </div>
      )}
    </div>
  )
}

function SimulationReportView({ report }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-accent/30 bg-surface p-3">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 rounded bg-amber-500/10 border border-amber-500/30 px-2 py-1 text-[10px] font-mono font-bold text-amber-300 uppercase tracking-wide">
          <ShieldAlert className="h-3 w-3" /> Simulated — Not Real Audience Data
        </span>
        <span className="text-[10px] font-mono text-text-faint">{report.model_version}</span>
      </div>

      <div className="flex flex-col gap-2">
        {report.segment_reactions.map((reaction) => (
          <div key={reaction.segment_id} className="rounded border border-border bg-surface-2 p-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-text">{reaction.segment_label}</span>
              <span className="text-[10px] font-mono text-text-muted">
                Appeal (est.): {Math.round(reaction.appeal_score * 100)}%
              </span>
            </div>
            <p className="text-[11px] text-text-muted mt-1 leading-relaxed">
              {reaction.credibility_assessment}
            </p>
            {reaction.objections?.length > 0 && (
              <div className="mt-1.5">
                <span className="text-[10px] font-mono font-bold text-text-faint uppercase">Objections</span>
                <ul className="list-disc list-inside text-[10px] text-text-muted mt-0.5">
                  {reaction.objections.map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
              </div>
            )}
            {reaction.confusing_claims?.length > 0 && (
              <div className="mt-1.5">
                <span className="text-[10px] font-mono font-bold text-text-faint uppercase">Confusing Claims</span>
                <ul className="list-disc list-inside text-[10px] text-text-muted mt-0.5">
                  {reaction.confusing_claims.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {reaction.compliance_risks?.length > 0 && (
              <div className="mt-1.5 flex items-start gap-1 text-[10px] text-amber-300">
                <ShieldAlert className="h-3 w-3 shrink-0 mt-0.5" />
                <span>{reaction.compliance_risks.join("; ")}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {report.recommended_angles?.length > 0 && (
        <div>
          <span className="text-[10px] font-mono font-bold text-text-faint uppercase">
            Recommended Angles
          </span>
          <ul className="list-disc list-inside text-[11px] text-text-muted mt-0.5">
            {report.recommended_angles.map((angle, i) => (
              <li key={i}>{angle}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-[10px] text-text-faint leading-relaxed">
        {report.assumptions?.join(" ")}
      </p>
    </div>
  )
}
