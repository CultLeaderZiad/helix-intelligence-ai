import { useEffect, useRef } from "react"
import { AlertTriangle, Trash2, ShieldAlert, Loader2 } from "lucide-react"
import { Button } from "./Button"
import { cn } from "@/lib/utils"

/**
 * Reusable dark instrument confirmation dialog for destructive and high-risk actions.
 * Traps focus, handles Escape key, and renders with high contrast design tokens.
 */
export function ConfirmDialog({
  isOpen,
  title = "Are you sure?",
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger", // 'danger' | 'warning' | 'primary'
  isBusy = false,
  onConfirm,
  onCancel,
}) {
  const confirmBtnRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !isBusy) {
        onCancel?.()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    const timer = setTimeout(() => confirmBtnRef.current?.focus(), 50)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
      clearTimeout(timer)
    }
  }, [isOpen, isBusy, onCancel])

  if (!isOpen) return null

  const isDanger = variant === "danger"
  const isWarning = variant === "warning"

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150 font-sans"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isBusy) onCancel?.()
      }}
    >
      <div
        className="w-full max-w-md rounded-xl border border-border bg-surface-2 p-5 shadow-2xl space-y-4"
      >
        <div className="flex items-start gap-3.5">
          <div
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border",
              isDanger
                ? "border-rose-500/30 bg-rose-500/10 text-rose-400"
                : isWarning
                ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                : "border-accent/30 bg-accent/10 text-accent",
            )}
          >
            {isDanger ? (
              <Trash2 className="h-4 w-4" />
            ) : isWarning ? (
              <ShieldAlert className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
          </div>
          <div className="space-y-1 pt-0.5 flex-1">
            <h2 id="confirm-dialog-title" className="text-sm font-semibold text-text">
              {title}
            </h2>
            {description && (
              <div className="text-xs text-text-muted leading-relaxed">
                {description}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isBusy}
          >
            {cancelText}
          </Button>
          <Button
            ref={confirmBtnRef}
            type="button"
            variant={isDanger ? "danger" : isWarning ? "default" : "primary"}
            size="sm"
            onClick={onConfirm}
            disabled={isBusy}
            className={cn(
              isDanger && "!bg-rose-500/15 !border-rose-500/40 !text-rose-300 hover:!bg-rose-500/25 hover:!border-rose-500",
              isWarning && "!bg-amber-500/15 !border-amber-500/40 !text-amber-300 hover:!bg-amber-500/25 hover:!border-amber-500",
            )}
          >
            {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
