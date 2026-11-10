import { useEffect, useId, useRef } from "react"
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
  const titleId = useId()
  const descriptionId = useId()
  const confirmBtnRef = useRef(null)
  const dialogRef = useRef(null)
  const previouslyFocusedRef = useRef(null)
  const onConfirmRef = useRef(onConfirm)
  const onCancelRef = useRef(onCancel)
  const isBusyRef = useRef(isBusy)

  useEffect(() => {
    onConfirmRef.current = onConfirm
    onCancelRef.current = onCancel
    isBusyRef.current = isBusy
  }, [onConfirm, onCancel, isBusy])

  useEffect(() => {
    if (!isOpen) return
    previouslyFocusedRef.current = document.activeElement

    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !isBusyRef.current) {
        onCancelRef.current?.()
      } else if (e.key === "Tab") {
        if (!dialogRef.current) return
        const focusableElements = Array.from(dialogRef.current.querySelectorAll(
          'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
        )
        ).filter((element) => !element.hasAttribute("disabled"))
        if (!focusableElements.length) {
          e.preventDefault()
          dialogRef.current.focus()
          return
        }
        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]
        const focusIsOutside = !dialogRef.current.contains(document.activeElement)

        if (e.shiftKey && (focusIsOutside || document.activeElement === firstElement)) {
          e.preventDefault()
          lastElement.focus()
        } else if (!e.shiftKey && (focusIsOutside || document.activeElement === lastElement)) {
          e.preventDefault()
          firstElement.focus()
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    const initialFocus = confirmBtnRef.current?.disabled
      ? dialogRef.current
      : confirmBtnRef.current
    initialFocus?.focus()
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      if (previouslyFocusedRef.current?.isConnected) {
        previouslyFocusedRef.current.focus()
      }
      previouslyFocusedRef.current = null
    }
  }, [isOpen])

  useEffect(() => {
    if (
      isOpen &&
      isBusy &&
      dialogRef.current?.contains(document.activeElement) &&
      document.activeElement instanceof HTMLElement &&
      document.activeElement.matches(":disabled")
    ) {
      dialogRef.current.focus()
    }
  }, [isOpen, isBusy])

  if (!isOpen) return null

  const isDanger = variant === "danger"
  const isWarning = variant === "warning"

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150 font-sans"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isBusyRef.current) onCancelRef.current?.()
      }}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
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
            <h2 id={titleId} className="text-sm font-semibold text-text">
              {title}
            </h2>
            {description && (
              <div id={descriptionId} className="text-xs text-text-muted leading-relaxed">
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
            onClick={() => onCancelRef.current?.()}
            disabled={isBusy}
           className="">
            {cancelText}
          </Button>
          <Button
            ref={confirmBtnRef}
            type="button"
            variant={isDanger ? "danger" : isWarning ? "default" : "primary"}
            size="sm"
            onClick={() => onConfirmRef.current?.()}
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
