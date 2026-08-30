import React, { useState, useEffect } from "react"
import { adminService } from "@/services"
import { Flag, Sliders, CheckCircle2, RefreshCw, ShieldCheck, Zap } from "lucide-react"

export function FeatureFlagsPage() {
  const [plans, setPlans] = useState([])
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const ALL_FEATURES = [
    { 
      key: "discover", 
      label: "Discover Search & Scraper Network", 
      description: "Allows running searches across Meta Ad Library, Bright Data, and Apify scraper backends." 
    },
    { 
      key: "intelligence", 
      label: "Brand Intelligence & Competitor Tracking", 
      description: "Aggregates multi-brand positioning, timeline velocity, and creative fatigue radar." 
    },
    { 
      key: "create", 
      label: "AI Creative Generation & Remix Engine", 
      description: "Generates variations, ad copy hooks, and visual scripts using Groq LLM." 
    },
    { 
      key: "performance", 
      label: "Performance Analytics & Hook Scoring", 
      description: "Calculates virality scores, estimated impression heatmaps, and format ratios." 
    },
    { 
      key: "swipe_files", 
      label: "Swipe Files & Moodboards", 
      description: "Enables saving creatives to custom swipe files and client presentation boards." 
    },
    { 
      key: "team_accounts", 
      label: "Multi-Seat Team Accounts", 
      description: "Allows inviting team members with role-based access control under one organization." 
    },
    { 
      key: "public_api", 
      label: "Public Developer API & Webhooks", 
      description: "Exposes REST endpoints and webhooks for programmatic pipeline execution." 
    },
  ]

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [plansData, orgsData] = await Promise.all([
        adminService.listPlans(),
        adminService.listOrganizations(),
      ])
      setPlans(Array.isArray(plansData) ? plansData : [])
      setOrgs(Array.isArray(orgsData) ? orgsData : [])
    } catch (err) {
      setError(err.message || "Failed to load feature flag matrix")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Flag className="w-7 h-7 text-indigo-400" />
            Platform Feature Flags & Matrix
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Global feature definitions and entitlement matrix across plans and organizations.
          </p>
        </div>
        <button
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Feature Definitions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ALL_FEATURES.map((feat) => (
          <div key={feat.key} className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Zap className="w-4 h-4 text-indigo-400" />
                {feat.label}
              </span>
              <span className="text-xs font-mono text-slate-500">{feat.key}</span>
            </div>
            <p className="text-xs text-slate-400">{feat.description}</p>
          </div>
        ))}
      </div>

      {/* Matrix Table */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-slate-400">
          Plan Entitlement Matrix
        </h3>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Feature</th>
                {plans.map((p) => (
                  <th key={p.id} className="py-3 px-4 text-center">{p.name}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {ALL_FEATURES.map((feat) => (
                <tr key={feat.key} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-sans font-medium text-slate-200">
                    {feat.label}
                  </td>
                  {plans.map((p) => {
                    const active = p.feature_flags && p.feature_flags[feat.key] !== false
                    return (
                      <td key={p.id} className="py-3 px-4 text-center">
                        {active ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px]">
                            Enabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-500 text-[11px]">
                            Disabled
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default FeatureFlagsPage
