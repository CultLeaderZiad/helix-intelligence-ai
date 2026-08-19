import { cn } from "@/lib/utils"
import { Tag } from "@/components/ui/Tag"
import { ScoreBar } from "@/components/ui/Metric"
import { brandsById } from "@/data/brands"
import {
  formatCompact,
  formatDays,
  formatInt,
  formatPercent,
  formatSpendBand,
  formatRelative,
} from "@/lib/format"

const PLATFORM_LABEL = {
  meta: "Meta",
  tiktok: "TikTok",
  youtube: "YouTube",
  linkedin: "LinkedIn",
  reddit: "Reddit",
}

/**
 * Dense result table — the default view, because scanning 20 rows beats
 * scrolling 20 cards. Row selection is keyboard-navigable and the header
 * is sticky so the column meaning never scrolls away.
 *
 * NOTE: brand lookup reads a fixture map here purely to resolve display
 * names the list endpoint does not embed. When FastAPI ships, the list
 * response will include `brand_name` and this import disappears.
 */
export function ResultsTable({ items, selectedId, onSelect }) {
  function handleKeyDown(event, index) {
    if (event.key === "ArrowDown") {
      event.preventDefault()
      const next = items[Math.min(index + 1, items.length - 1)]
      if (next) onSelect(next.id)
    }
    if (event.key === "ArrowUp") {
      event.preventDefault()
      const prev = items[Math.max(index - 1, 0)]
      if (prev) onSelect(prev.id)
    }
  }

  return (
    <div className="min-w-0 flex-1 overflow-auto">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-border-strong">
            <th scope="col" className="label-mono px-3 py-2 font-normal">
              Creative
            </th>
            <th scope="col" className="label-mono w-[104px] px-2 py-2 font-normal">
              Brand
            </th>
            <th scope="col" className="label-mono w-[72px] px-2 py-2 font-normal">
              Platform
            </th>
            <th scope="col" className="label-mono w-[112px] px-2 py-2 font-normal">
              Composite
            </th>
            <th scope="col" className="label-mono w-[64px] px-2 py-2 text-right font-normal">
              Impr.
            </th>
            <th scope="col" className="label-mono w-[52px] px-2 py-2 text-right font-normal">
              ER
            </th>
            <th scope="col" className="label-mono w-[52px] px-2 py-2 text-right font-normal">
              Spend
            </th>
            <th scope="col" className="label-mono w-[60px] px-3 py-2 text-right font-normal">
              Active
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((c, i) => {
            const brand = brandsById[c.brand_id]
            const active = c.id === selectedId
            return (
              <tr
                key={c.id}
                tabIndex={0}
                onClick={() => onSelect(c.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSelect(c.id)
                  handleKeyDown(e, i)
                }}
                aria-selected={active}
                className={cn(
                  "cursor-pointer border-b border-border transition-colors focus:outline-none",
                  active
                    ? "bg-surface-3"
                    : "hover:bg-surface-2 focus-visible:bg-surface-2",
                )}
              >
                <td className="max-w-0 px-3 py-2">
                  <div className="flex items-center gap-2">
                    {active ? (
                      <span className="h-3 w-0.5 shrink-0 bg-accent" aria-hidden="true" />
                    ) : null}
                    <div className="min-w-0">
                      <p className="truncate text-[13px] text-text">{c.headline}</p>
                      <p className="truncate text-[11px] text-text-faint">
                        {c.landing_domain ?? "no landing page"}
                        {c.variant_count
                          ? ` · ${formatInt(c.variant_count)} variants`
                          : ""}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-2 py-2">
                  <span className="block truncate text-xs text-text-muted">
                    {brand?.name ?? "Unknown"}
                  </span>
                </td>
                <td className="px-2 py-2">
                  <Tag>{PLATFORM_LABEL[c.platform] ?? c.platform}</Tag>
                </td>
                <td className="px-2 py-2">
                  {c.scores?.composite === null || c.scores?.composite === undefined ? (
                    <span className="label-mono">unscored</span>
                  ) : (
                    <ScoreBar value={c.scores.composite} />
                  )}
                </td>
                <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                  {formatCompact(c.metrics?.impressions_est)}
                </td>
                <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                  {c.metrics?.engagement_rate === null ||
                  c.metrics?.engagement_rate === undefined
                    ? "—"
                    : formatPercent(c.metrics.engagement_rate)}
                </td>
                <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                  {formatSpendBand(c.metrics?.spend_band)}
                </td>
                <td className="tnum px-3 py-2 text-right font-mono text-[11px] text-text-faint">
                  {c.days_active ? formatDays(c.days_active) : formatRelative(c.first_seen)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
