import { Button } from "@/components/ui/Button"
import { useW9Copy } from "@/i18n/w9Product"

/**
 * "Already have this" choice before a Discover run: open a recent stored
 * search for 0 records, or run a fresh one at its estimated record cost.
 */
export function StoredResultsPrompt({ stored, estimate, onView, onFresh, onCancel }) {
  const w9 = useW9Copy()
  if (!stored) return null
  return (
    <div role="dialog" aria-labelledby="stored-results-title" className="space-y-2 border-b border-border bg-surface px-4 py-3 text-sm">
      <p id="stored-results-title" className="font-semibold">{w9.storedTitle}</p>
      <p className="text-text-muted">{w9.storedBody(stored.total ?? 0, String(stored.searched_at || "").slice(0, 10))}</p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="primary" onClick={onView}>{w9.storedView}</Button>
        <Button size="sm" onClick={onFresh}>{w9.storedFresh(estimate)}</Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>{w9.storedCancel}</Button>
      </div>
    </div>
  )
}

export default StoredResultsPrompt
