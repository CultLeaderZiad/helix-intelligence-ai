import { Button } from "@/components/ui/Button"
import { formatDuration, formatInt } from "@/lib/format"
import { useLanguage } from "@/context/LanguageContext"
import w5Discover from "@/i18n/w5Discover"

export function JobProgress({ job, query, onCancel = null, onRetry = null, cancelError = null, isCancelling = false, showRetry = false }) {
  const { lang } = useLanguage()
  const copy = w5Discover[lang] ?? w5Discover.en
  if (!job) return null
  const failed = job.status === "failed"
  const timedOut = job.status === "timed_out"
  const cancelled = job.status === "cancelled" || job.status === "canceled"
  const done = job.status === "succeeded"
  const active = !failed && !timedOut && !cancelled && !done
  const status = failed ? copy.statusFailed : timedOut ? copy.statusTimedOut : cancelled ? copy.statusCancelled : done ? copy.statusSucceeded : cancelError ? copy.statusCancelError : isCancelling ? copy.statusCancelling : job.status === "queued" ? copy.statusQueued : copy.statusRunning
  const progress = typeof job.progress === "number" ? Math.max(0, Math.min(1, job.progress)) : null
  const stageLabel = job.stage_label?.trim()
  return (
    <div role="status" aria-live="polite" aria-busy={active} dir={lang === "ar" ? "rtl" : "ltr"} className="shrink-0 space-y-2 border-b border-border bg-bg px-3 py-3 font-mono text-xs">
      <div className="flex flex-wrap items-center gap-3">
        <span className={failed || timedOut ? "text-danger" : "text-text"}>{status}</span>
        <span className="truncate text-text-muted">discover/{job.job_id}</span>
        <span className="ms-auto text-text-faint">{formatDuration(job.elapsed_ms)}</span>
        {active && onCancel && <Button size="xs" variant="ghost" onClick={onCancel} disabled={isCancelling}>{cancelError ? copy.retryCancel : isCancelling ? copy.statusCancelling : copy.cancel}</Button>}
        {!active && showRetry && onRetry && <Button size="xs" onClick={onRetry}>{copy.retry}</Button>}
      </div>
      <p className="truncate text-text-muted">$ query &quot;{query?.trim() || "*"}&quot;</p>
      {active && stageLabel && <p className="text-text-muted">{job.status === "queued" ? copy.statusQueued : stageLabel}</p>}
      {active && progress !== null && <div role="progressbar" aria-label={status} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)} className="h-0.5 bg-surface-3"><div className="h-full bg-accent" style={{ width: `${progress * 100}%` }} /></div>}
      {done && typeof job.records_found === "number" && <p>{formatInt(job.records_found)} {copy.recordsFound}</p>}
      {failed && <p className="text-danger">{lang === "ar" ? copy.failed : job.error || copy.failed}</p>}
      {timedOut && <p className="text-danger">{copy.timedOut}</p>}
      {cancelled && <p className="text-text-muted">{copy.cancelled}</p>}
      {cancelError && <p role="alert" className="text-danger">{copy.cancelError}</p>}
    </div>
  )
}
