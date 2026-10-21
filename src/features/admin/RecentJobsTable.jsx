import { Tag } from "@/components/ui/Tag"
import { formatInt, formatDuration } from "@/lib/format"
import { useLanguage } from "@/context/LanguageContext"
import { adminMessage, adminStatusLabel, formatAdminRelative } from "@/i18n/adminMessages"

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
  const { lang } = useLanguage()
  return (
    <div className="min-w-0 overflow-auto">
      <table className="w-full min-w-[620px] table-fixed border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-border-strong">
            <th scope="col" className="label-mono w-[94px] px-3 py-2 font-normal">
              {adminMessage(lang, "Job")}
            </th>
            <th scope="col" className="label-mono w-[132px] px-2 py-2 font-normal">
              {adminMessage(lang, "Organization")}
            </th>
            <th scope="col" className="label-mono px-2 py-2 font-normal">
              {adminMessage(lang, "Query")}
            </th>
            <th scope="col" className="label-mono w-[86px] px-2 py-2 font-normal">
              {adminMessage(lang, "Status")}
            </th>
            <th scope="col" className="label-mono w-[68px] px-2 py-2 text-right font-normal">
              {adminMessage(lang, "Records")}
            </th>
            <th scope="col" className="label-mono w-[68px] px-2 py-2 text-right font-normal">
              {adminMessage(lang, "Duration")}
            </th>
            <th scope="col" className="label-mono w-[76px] px-3 py-2 text-right font-normal">
              {adminMessage(lang, "Age")}
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 ? (
            <tr><td colSpan={7} className="px-3 py-8 text-center text-text-faint">{adminMessage(lang, "No recent jobs found.")}</td></tr>
          ) : jobs.map((job) => (
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
                <Tag className="" tone={STATUS_TONE[job.status] ?? "default"}>{adminStatusLabel(lang, job.status)}</Tag>
              </td>
              <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                {job.records ? formatInt(job.records) : "—"}
              </td>
              <td className="tnum px-2 py-2 text-right font-mono text-[11px] text-text-muted">
                {job.duration_ms ? formatDuration(job.duration_ms) : "—"}
              </td>
              <td className="tnum whitespace-nowrap px-3 py-2 text-right font-mono text-[11px] text-text-faint">
                {formatAdminRelative(job.created_at, lang)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
