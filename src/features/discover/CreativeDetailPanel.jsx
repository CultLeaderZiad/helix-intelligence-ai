import { X, ExternalLink } from "lucide-react"
import { creativeService } from "@/services"
import { useAsync } from "@/hooks/useAsync"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { ScoreBar, StatBlock, MetricValue } from "@/components/ui/Metric"
import { ErrorState, Skeleton } from "@/components/ui/States"
import {
  formatCompact,
  formatDate,
  formatPercent,
  formatSpendBand,
} from "@/lib/format"

/**
 * Right-hand inspector. Uses the *detail* endpoint rather than the row
 * already in memory, because the detail contract hydrates relations
 * (brand, patterns) that the list contract deliberately omits — the same
 * split FastAPI will have.
 */
export function CreativeDetailPanel({ creativeId, onClose }) {
  const { data, error, loading, refetch } = useAsync(
    () => creativeService.getCreativeById(creativeId),
    [creativeId],
    { enabled: Boolean(creativeId) },
  )

  return (
    <aside
      className="flex w-full shrink-0 flex-col overflow-hidden border-l border-border bg-surface lg:w-[320px]"
      aria-label="Creative detail"
    >
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-border px-3">
        <span className="label-mono">Inspector</span>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close inspector">
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3 p-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : null}

      {error ? <ErrorState error={error} onRetry={refetch} /> : null}

      {data ? (
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-3">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-1">
              <Tag tone="strong">{data.platform}</Tag>
              <Tag>{data.format}</Tag>
              {data.duration_seconds ? <Tag>{data.duration_seconds}s</Tag> : null}
              {data.thumbnail_ratio ? <Tag>{data.thumbnail_ratio}</Tag> : null}
            </div>
            <h3 className="text-pretty text-sm leading-snug text-text">{data.headline}</h3>
            {data.body ? (
              <p className="text-pretty text-xs leading-relaxed text-text-muted">
                {data.body}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-2 border-t border-border pt-3">
            <span className="label-mono">Brand</span>
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[13px] text-text">
                {data.brand?.name ?? "Unknown"}
              </span>
              {data.brand?.ad_count !== undefined ? (
                <MetricValue value={formatCompact(data.brand.ad_count)} unit="ads" muted />
              ) : null}
            </div>
            {data.landing_domain ? (
              <span className="flex items-center gap-1 font-mono text-[11px] text-text-faint">
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
                {data.landing_domain}
              </span>
            ) : null}
          </div>

          <div className="flex flex-col gap-2.5 border-t border-border pt-3">
            <span className="label-mono">Scores</span>
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
                  <ScoreBar value={value} width="w-16" />
                )}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
            <StatBlock
              label="Impressions"
              value={formatCompact(data.metrics?.impressions_est)}
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
            <StatBlock label="First seen" value={formatDate(data.first_seen)} />
            <StatBlock label="Last seen" value={formatDate(data.last_seen)} />
          </div>

          <div className="flex flex-col gap-2 border-t border-border pt-3">
            <span className="label-mono">Patterns</span>
            {data.patterns?.length ? (
              <div className="flex flex-col gap-1.5">
                {data.patterns.map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-text">{p.label}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      <span className="label-mono">{p.family}</span>
                      <MetricValue
                        value={p.lift_index.toFixed(2)}
                        unit="lift"
                        className="text-[11px]"
                      />
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-faint">
                No patterns attributed. Pattern mining runs in the Intelligence loop.
              </p>
            )}
          </div>

          <p className="mt-auto border-t border-border pt-3 font-mono text-[10px] text-text-faint">
            {data.id}
          </p>
        </div>
      ) : null}
    </aside>
  )
}
