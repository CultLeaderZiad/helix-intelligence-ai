import React, { useEffect, useState } from "react"
import { Activity, BarChart2, TrendingUp, Users } from "lucide-react"
import { dashboardService } from "@/services"
import { Panel } from "@/components/ui/Panel"
import { Tag } from "@/components/ui/Tag"

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedBrands, setSelectedBrands] = useState([])

  useEffect(() => {
    async function loadData() {
      try {
        const result = await dashboardService.getMetrics()
        setData(result)
        if (result.cross_brand && result.cross_brand.length > 0) {
          // Pre-select up to 3 brands for comparison
          setSelectedBrands(result.cross_brand.slice(0, 3).map(b => b.brand_id))
        }
      } catch (err) {
        setError(err.message || "Failed to load dashboard data")
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center font-mono text-sm text-text-faint">
          Loading dashboard metrics...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center font-mono text-sm text-red-400">
          Error: {error}
        </div>
      </div>
    )
  }

  const toggleBrand = (brandId) => {
    if (selectedBrands.includes(brandId)) {
      setSelectedBrands(prev => prev.filter(id => id !== brandId))
    } else {
      if (selectedBrands.length >= 3) {
        // Replace the last one
        setSelectedBrands(prev => [...prev.slice(0, 2), brandId])
      } else {
        setSelectedBrands(prev => [...prev, brandId])
      }
    }
  }

  const comparisonBrands = (data?.cross_brand || []).filter(b => selectedBrands.includes(b.brand_id))

  // Find max count for timeline charting
  const maxCount = Math.max(...(data?.timeline || []).map(t => t.count), 1)

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-background p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-text">Workspace Dashboard</h1>
        <p className="mt-1 font-mono text-xs text-text-muted">
          Cross-brand analytics & creative performance
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        
        {/* TOP PERFORMERS */}
        <Panel className="flex flex-col">
          <div className="border-b border-border p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
              <TrendingUp className="h-4 w-4 text-accent" />
              Top Performers
            </h2>
            <p className="font-mono text-[10px] uppercase text-text-faint">
              Ranked by composite score
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="flex flex-col gap-3">
              {(data?.top_performers || []).length === 0 ? (
                <div className="text-sm text-text-faint">No scored creatives found.</div>
              ) : (
                data.top_performers.map((creative, i) => (
                  <div key={creative.id} className="flex items-center justify-between rounded-md border border-border/50 bg-surface-2 p-3">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-text truncate max-w-[200px]">{creative.headline || creative.brand_id}</span>
                      <span className="font-mono text-[10px] text-text-muted">{creative.format.toUpperCase()} · {creative.brand_id}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-lg font-bold text-accent">
                        {creative.scores?.composite != null ? creative.scores.composite.toFixed(1) : "—"}
                      </span>
                      <span className="font-mono text-[10px] text-text-faint">SCORE</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </Panel>

        {/* REACH/ACTIVITY LEADERBOARD */}
        <Panel className="flex flex-col">
          <div className="border-b border-border p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
              <Users className="h-4 w-4 text-accent" />
              Reach & Activity
            </h2>
            <p className="font-mono text-[10px] uppercase text-text-faint">
              Ranked by estimated impressions or days active
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="flex flex-col gap-3">
              {(data?.reach_leaderboard || []).length === 0 ? (
                <div className="text-sm text-text-faint">No reach data available.</div>
              ) : (
                data.reach_leaderboard.map((creative, i) => {
                  const hasReach = creative.metrics?.impressions_est > 0
                  const value = hasReach ? creative.metrics.impressions_est.toLocaleString() : creative.days_active
                  const label = hasReach ? "IMPRESSIONS (EST)" : "DAYS ACTIVE"
                  
                  return (
                    <div key={creative.id} className="flex items-center justify-between rounded-md border border-border/50 bg-surface-2 p-3">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-text truncate max-w-[200px]">{creative.headline || creative.brand_id}</span>
                        <span className="font-mono text-[10px] text-text-muted">{creative.format.toUpperCase()} · {creative.brand_id}</span>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="font-mono text-sm font-bold text-text">
                          {value}
                        </span>
                        <span className="font-mono text-[9px] text-text-faint">{label}</span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </Panel>

        {/* TIMELINE VIEW */}
        <Panel className="col-span-1 md:col-span-2">
          <div className="border-b border-border p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
              <Activity className="h-4 w-4 text-accent" />
              Discovery Activity Over Time
            </h2>
            <p className="font-mono text-[10px] uppercase text-text-faint">
              Creatives found per day
            </p>
          </div>
          <div className="p-6">
            {(data?.timeline || []).length === 0 ? (
              <div className="text-sm text-text-faint">No timeline data available.</div>
            ) : (
              <div className="flex h-40 items-end gap-2">
                {data.timeline.map((point, i) => {
                  const heightPercent = Math.max((point.count / maxCount) * 100, 5) // min 5% for visibility
                  return (
                    <div key={i} className="group relative flex flex-1 flex-col justify-end items-center h-full">
                      <div 
                        className="w-full rounded-t-sm bg-accent/40 transition-all group-hover:bg-accent" 
                        style={{ height: `${heightPercent}%` }}
                      ></div>
                      <div className="absolute -top-8 hidden rounded bg-surface px-2 py-1 font-mono text-[10px] text-text shadow-lg group-hover:block whitespace-nowrap z-10 border border-border">
                        {point.date}: {point.count}
                      </div>
                      <span className="mt-2 block font-mono text-[9px] text-text-faint truncate max-w-full">
                        {new Date(point.date).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </Panel>

        {/* CROSS-BRAND COMPARISON */}
        <Panel className="col-span-1 md:col-span-2 flex flex-col">
          <div className="border-b border-border p-4 flex justify-between items-center">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
                <BarChart2 className="h-4 w-4 text-accent" />
                Cross-Brand Comparison
              </h2>
              <p className="font-mono text-[10px] uppercase text-text-faint">
                Select 2-3 brands to compare
              </p>
            </div>
            <div className="flex gap-2">
              {(data?.cross_brand || []).map(b => (
                <button
                  key={b.brand_id}
                  onClick={() => toggleBrand(b.brand_id)}
                  className={`px-2 py-1 text-xs font-mono rounded ${
                    selectedBrands.includes(b.brand_id) 
                      ? "bg-accent/20 text-accent border border-accent/50" 
                      : "bg-surface-2 text-text-muted border border-border hover:text-text"
                  }`}
                >
                  {b.name}
                </button>
              ))}
            </div>
          </div>
          
          <div className="p-6">
            {comparisonBrands.length === 0 ? (
              <div className="text-sm text-text-faint">Select brands above to compare.</div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                {comparisonBrands.map(brand => (
                  <div key={brand.brand_id} className="rounded-xl border border-border bg-surface-2 p-5 shadow-sm">
                    <h3 className="mb-4 text-lg font-bold text-text truncate">{brand.name}</h3>
                    
                    <div className="space-y-4">
                      <div>
                        <p className="font-mono text-[10px] text-text-faint uppercase">Avg Composite Score</p>
                        <p className="font-mono text-2xl font-bold text-accent">
                          {brand.avg_score != null ? brand.avg_score.toFixed(1) : "—"}
                        </p>
                      </div>
                      
                      <div>
                        <p className="font-mono text-[10px] text-text-faint uppercase">Active Ads</p>
                        <p className="text-base font-medium text-text">{brand.active_ads}</p>
                      </div>
                      
                      <div>
                        <p className="font-mono text-[10px] text-text-faint uppercase">Dominant Format</p>
                        <Tag variant="accent" className="mt-1">{brand.dominant_format.toUpperCase()}</Tag>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>

      </div>
    </div>
  )
}
