import { useState } from "react"
import { X, ExternalLink, Play, Image as ImageIcon, Layers, Bookmark, Check } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { creativeService } from "@/services"
import { useAsync } from "@/hooks/useAsync"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { ScoreBar, StatBlock, MetricValue } from "@/components/ui/Metric"
import { ErrorState, Skeleton } from "@/components/ui/States"
import { deriveInsight } from "@/lib/insight"
import {
  formatCompact,
  formatConfidence,
  formatDate,
  formatDays,
  formatDuration,
  formatLift,
  formatPercent,
  formatOrdinal,
  formatPrevalence,
  formatSpendBand,
} from "@/lib/format"

const FORMAT_ICON = { video: Play, image: ImageIcon, carousel: Layers }

/**
 * Media frame — the creative itself is the hero of the inspector.
 *
 * The mock source does not sync binary assets, so the frame renders the
 * creative's true geometry (ratio, format, duration) and says so plainly
 * instead of faking a thumbnail. When the API embeds `media_url`, the
 * inner block becomes an <img>/<video> and nothing else moves.
 */
function MediaFrame({ format, ratio, duration }) {
  const Icon = FORMAT_ICON[format] ?? ImageIcon
  const aspect = ratio ? ratio.replace(":", " / ") : "16 / 9"

  return (
    <div className="flex justify-center border-b border-border bg-bg p-4">
      <div
        className="grid-backdrop relative flex max-h-64 w-full items-center justify-center border border-border bg-surface"
        style={{ aspectRatio: aspect, maxWidth: ratio === "9:16" ? "9rem" : "100%" }}
      >
        <div className="flex flex-col items-center gap-2">
          <Icon className="h-5 w-5 text-text-faint" aria-hidden="true" />
          <span className="label-mono">asset not synced</span>
        </div>
        <span className="label-mono absolute left-2 top-2">{format}</span>
        <span className="label-mono absolute right-2 top-2">{ratio}</span>
        {duration ? (
          <span className="label-mono tnum absolute bottom-2 right-2">
            {formatDuration(duration * 1000)}
          </span>
        ) : null}
      </div>
    </div>
  )
}

/**
 * WHY THIS AD MATTERS — research finding, not marketing copy.
 * Every line is derived from the record (see lib/insight.js).
 */
function InsightBlock({ creative }) {
  const insight = deriveInsight(creative)
  if (!insight) return null

  return (
    <div className="flex flex-col gap-3 border border-border bg-surface-2 p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="label-mono text-text">Why this ad matters</span>
        <span className="label-mono tnum">
          confidence {formatConfidence(insight.confidence)}
        </span>
      </div>

      {insight.daysActive ? (
        <p className="text-xs leading-relaxed text-text-muted">
          This creative has been active for{" "}
          <span className="tnum font-mono text-text">
            {formatDays(insight.daysActive)}
          </span>
          {insight.daysActive >= 60 ? " — well past the typical fatigue window." : "."}
        </p>
      ) : null}

      <ol className="flex flex-col gap-2">
        {insight.reasons.map((r, i) => (
          <li key={r.id} className="flex items-baseline gap-2.5">
            <span className="label-mono tnum shrink-0 text-text-faint">
              {formatOrdinal(i + 1)}
            </span>
            <span className="min-w-0 flex-1 truncate text-xs text-text">{r.label}</span>
            <span className="label-mono tnum shrink-0">{formatLift(r.lift)} lift</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

/** Numbered pattern findings — research results, not feature cards. */
function PatternFindings({ patterns }) {
  if (!patterns?.length) {
    return (
      <p className="text-xs text-text-faint">
        No patterns attributed. Pattern mining runs in the Intelligence loop.
      </p>
    )
  }
  return (
    <div className="flex flex-col">
      {patterns.map((p, i) => (
        <div
          key={p.id}
          className="flex flex-col gap-1 border-b border-border py-2.5 first:pt-0 last:border-b-0 last:pb-0"
        >
          <div className="flex items-baseline gap-2">
            <span className="label-mono tnum w-5 shrink-0 text-text-faint">
              {formatOrdinal(i + 1)}
            </span>
            <span className="text-xs text-text">{p.label}</span>
            <span className="label-mono ml-auto">{p.family}</span>
          </div>
          <p className="pl-7 text-[11px] leading-relaxed text-text-muted">
            Found in{" "}
            <span className="tnum font-mono text-text">
              {formatPrevalence(p.prevalence)}
            </span>{" "}
            of the corpus · lift{" "}
            <span className="tnum font-mono text-text">{formatLift(p.lift_index)}</span>
          </p>
        </div>
      ))}
    </div>
  )
}

/**
 * Right-hand inspector. Uses the *detail* endpoint rather than the row
 * already in memory, because the detail contract hydrates relations
 * (brand, patterns) that the list contract deliberately omits — the same
 * split FastAPI will have.
 */
export function CreativeDetailPanel({ creativeId, onClose }) {
  const { user } = useAuth()
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const { data, error, loading, refetch } = useAsync(
    () => creativeService.getCreativeById(creativeId),
    [creativeId],
    { enabled: Boolean(creativeId) },
  )

  const showSwipeOption = user?.feature_flags?.swipe_files !== false

  const handleToggleSave = async () => {
    if (!creativeId || saving) return
    setSaving(true)
    try {
      if (saved) {
        await creativeService.unsaveCreative(creativeId)
        setSaved(false)
      } else {
        await creativeService.saveCreative(creativeId)
        setSaved(true)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <aside
      className="flex w-full shrink-0 flex-col overflow-hidden border-l border-border bg-surface lg:w-[344px]"
      aria-label="Creative detail"
    >
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-border px-3">
        <span className="label-mono">Inspector</span>
        <div className="flex items-center gap-1">
          {showSwipeOption && data ? (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleToggleSave}
              disabled={saving}
              className={saved ? "text-accent" : "text-text-muted hover:text-text"}
              aria-label={saved ? "Remove from swipe file" : "Save to swipe file"}
              title={saved ? "Saved in swipe files" : "Save to swipe files (0 credits)"}
            >
              {saved ? (
                <Check className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
              ) : (
                <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </Button>
          ) : null}
          <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close inspector">
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3 p-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-3 w-32" />
        </div>
      ) : null}

      {error ? <ErrorState error={error} onRetry={refetch} /> : null}

      {data ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <MediaFrame
            format={data.format}
            ratio={data.thumbnail_ratio}
            duration={data.duration_seconds}
          />

          <div className="flex flex-col gap-4 p-3">
            {/* Brand + copy — hierarchy: brand, headline, body */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-xs font-medium text-text">
                    {data.brand?.name ?? "Unknown brand"}
                  </span>
                  <Tag>{data.platform}</Tag>
                  {data.data_source === "organic_content_proxy" ? (
                    <span className="rounded border border-amber-500/20 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-amber-400" title="Organic Post/Reel Proxy Content">
                      Organic Proxy
                    </span>
                  ) : null}
                </span>
                {data.brand?.ad_count !== undefined ? (
                  <MetricValue
                    value={formatCompact(data.brand.ad_count)}
                    unit="ads"
                    muted
                    className="text-[11px]"
                  />
                ) : null}
              </div>
              <h3 className="text-pretty text-sm font-medium leading-snug text-text">
                {data.headline}
              </h3>
              {data.body ? (
                <p className="text-pretty text-xs leading-relaxed text-text-muted">
                  {data.body}
                </p>
              ) : null}
              {data.landing_domain ? (
                <span className="flex items-center gap-1 pt-0.5 font-mono text-[11px] text-text-faint">
                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  {data.landing_domain}
                </span>
              ) : null}
            </div>

            {/* Active duration — position 4 in the hierarchy */}
            <div className="flex items-center gap-3 border-y border-border py-2">
              <StatBlock label="Active" value={formatDays(data.days_active)} />
              <StatBlock label="First seen" value={formatDate(data.first_seen)} />
              <StatBlock label="Last seen" value={formatDate(data.last_seen)} />
            </div>

            <InsightBlock creative={data} />

            {/* Performance scores */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="label-mono">Performance scores</span>
                {data.scores?.composite !== null && data.scores?.composite !== undefined ? (
                  <span className="label-mono text-accent">
                    tier {data.scores.composite >= 80 ? "A" : data.scores.composite >= 60 ? "B" : "C"}
                  </span>
                ) : null}
              </div>
              {[
                ["Hook", data.scores?.hook],
                ["Clarity", data.scores?.clarity],
                ["Retention", data.scores?.retention],
                ["Composite", data.scores?.composite],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-2">
                  <span className="text-xs text-text-muted">{label}</span>
                  {value === null || value === undefined ? (
                    <span className="label-mono">not scored</span>
                  ) : (
                    <ScoreBar value={value} width="w-20" />
                  )}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-3 border-t border-border pt-3">
              <StatBlock
                label={
                  <span className="flex items-center gap-1">
                    Impressions
                    {data.is_estimated && <span className="text-[9px] text-amber-500" title="Estimated from engagement">(est)</span>}
                  </span>
                }
                value={`~${formatCompact(data.metrics?.impressions_est)}`}
              />
              <StatBlock label="Spend" value={formatSpendBand(data.metrics?.spend_band)} />
              <StatBlock
                label="Engagement"
                value={
                  data.metrics?.engagement_rate === null ||
                  data.metrics?.engagement_rate === undefined
                    ? "—"
                    : formatPercent(data.metrics.engagement_rate)
                }
              />
              <StatBlock
                label="Est. CTR"
                value={
                  data.metrics?.ctr_est === null || data.metrics?.ctr_est === undefined
                    ? "—"
                    : formatPercent(data.metrics.ctr_est, 2)
                }
              />
            </div>

            <div className="flex flex-col gap-2 border-t border-border pt-3">
              <span className="label-mono">Pattern findings</span>
              <PatternFindings patterns={data.patterns} />
            </div>

            <p className="label-mono tnum border-t border-border pt-3">{data.id}</p>
          </div>
        </div>
      ) : null}
    </aside>
  )
}
