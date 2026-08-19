import { Tag } from "@/components/ui/Tag"
import { formatInt, formatDuration, formatRelative } from "@/lib/format"

/**
 * Dense, sticky-header table of recent cross-tenant scrape jobs — the
 * same scanning-first pattern as Discover's ResultsTable, rebuilt for the
 * operator's columns (which org, which status) rather than a creative's.
 * A shared generic table would have had to know about both; each stays
 * legible by owning its own columns.
 */

const STATUS_TONE = {
  queued: "default",
  running: "info",
  succeeded: "success",
  failed: "danger",
}

export function RecentJobsTable({ jobs }) {
  return (
    <div className="min-w-0 overflow-auto">
      <table className="w-full min-w-[620px] table-fixed border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-border-strong">
            <th scope="col" className="label-mono w-[94px] px-3 py-2 font-normal">
              Job
            </th>
            <th scope="col" className="label-mono w-[132px] px-2 py-2 font-normal">
              Organization
            </th>
            <th scope="col" className="label-mono px-2 py-2 font-normal">
              Query
            </th>
            <th scope="col" className="label-mono w-[86px] px-2 py-2 font-normal">
              Status
            </th>
            <th scope="col" className="label-mono w-[68px] px-2 py-2 text-right font-normal">
              Records
            </th>
            <th scope="col" className="label-mono w-[68px] px-2 py-2 text-right font-normal">
              Duration
            </th>
            <th scope="col" className="label-mono w-[76px] px-3 py-2 text-right font-normal">
              Age
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.job_id} className="border-b border-border">
              <td className="px-3 py-2">
                <span className="tnum font-mono text-[11px] text-text-muted">
                  {job.job_id}
                </span>
              </td>
              <td className="px-2 py-2">
                <span className="block truncate text-[13px] text-text">
                  {job.organization}
                </span>
              </td>
              <td className="px-2 py-2">
                <span className="block truncate text-xs text-text-muted">
                  {job.query}
                </span>
              </td>
              <td className="px-2 py-2">
                <Tag tone={STATUS_TONE[job.status] ?? "default"}>{job.status}</Tag>
              </td>
              <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                {job.records ? formatInt(job.records) : "—"}
              </td>
              <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                {job.duration_ms ? formatDuration(job.duration_ms) : "—"}
              </td>
              <td className="tnum whitespace-nowrap px-3 py-2 text-right font-mono text-[11px] text-text-faint">
                {formatRelative(job.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
